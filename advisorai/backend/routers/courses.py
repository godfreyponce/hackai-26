"""
Courses router — GET /api/courses

Search and browse UTD course catalog from Nebula data.
"""

import asyncio
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel

from services.data_loader import get_course_store
from services import nebula
from services.degree_plans import get_degree_plan, get_minor_plan, MINOR_PLANS
import httpx
import os

NEBULA_BASE = "https://api.utdnebula.com"
NEBULA_HEADERS = {"x-api-key": os.getenv("NEBULA_API_KEY", "")}

router = APIRouter()


@router.get("/")
async def list_courses(
    q: Optional[str] = Query(None, description="Search query"),
    department: Optional[str] = Query(None, description="Filter by department (e.g., CS)"),
    limit: int = Query(20, description="Max results"),
):
    """Search and browse UTD courses."""
    store = get_course_store()

    if q:
        results = store.search_courses(q, limit=limit)
    elif department:
        results = [
            info for code, info in store.courses.items()
            if code.startswith(department.upper())
        ][:limit]
    else:
        results = list(store.courses.values())[:limit]

    return [
        {
            "code": r.code,
            "name": r.title,
            "credits": r.credits,
            "description": r.description[:200] if r.description else "",
            "school": r.school,
            "prerequisites": store.get_prerequisites(r.code),
        }
        for r in results
    ]


@router.get("/prereqs-map")
async def get_prereqs_map(major: Optional[str] = Query("Computer Science", description="Student's major")):
    """
    Return the full prerequisite chain map for a given major's degree plan.
    Used by the frontend for drag-and-drop prerequisite validation.

    Returns:
        {prereqs: {course_code: [prereq_codes]}, completed_in_plan: [...]}
    """
    plan = get_degree_plan(major or "Computer Science")
    if not plan:
        return {"prereqs": {}}

    prereq_chains = plan.get("prerequisite_chains", {})
    return {"prereqs": prereq_chains}


@router.get("/minors")
async def list_supported_minors():
    """
    List all formally supported minors with their required courses.
    Useful for frontend to know what minors have structured plans.

    Returns:
        {minors: [{name, total_hours, required_courses, notes}]}
    """
    seen_names = set()
    minors = []

    for key, plan in MINOR_PLANS.items():
        name = plan.get("name", key)
        if name in seen_names:
            continue
        seen_names.add(name)

        minors.append({
            "name": name,
            "total_hours": plan.get("total_hours", 18),
            "required_courses": plan.get("required_courses", []),
            "subject_prefixes": plan.get("subject_prefixes", []),
            "notes": plan.get("notes", ""),
        })

    return {"minors": minors}


@router.get("/minors/{minor_name}")
async def get_minor_details(minor_name: str):
    """
    Get details for a specific minor.

    Args:
        minor_name: Minor name (e.g., "Finance", "Psychology")

    Returns:
        Full minor plan with required_courses, prerequisite_chains, etc.
    """
    plan = get_minor_plan(minor_name)
    if not plan:
        return {"error": f"Minor '{minor_name}' not found in our registry. The advisor can still help plan for this minor."}

    return {
        "name": plan.get("name", minor_name),
        "total_hours": plan.get("total_hours", 18),
        "required_courses": plan.get("required_courses", []),
        "prerequisite_chains": plan.get("prerequisite_chains", {}),
        "subject_prefixes": plan.get("subject_prefixes", []),
        "notes": plan.get("notes", ""),
    }


@router.get("/{course_code}")
async def get_course(course_code: str):
    """Get details for a specific course (e.g., CS+1337)."""
    # URL-encode spaces as + in the path
    code = course_code.replace("+", " ").upper()
    store = get_course_store()
    info = store.get_course(code)

    if not info:
        # Fallback: try Nebula API directly
        try:
            parts = code.split()
            if len(parts) >= 2:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(
                        f"{NEBULA_BASE}/course",
                        params={"subject_prefix": parts[0], "course_number": parts[1]},
                        headers=NEBULA_HEADERS,
                    )
                    if resp.status_code == 200:
                        courses = resp.json().get("data", [])
                        if courses:
                            c = courses[0]
                            return {
                                "code": code,
                                "name": c.get("title", code),
                                "credits": int(c.get("credit_hours", "3") or "3"),
                                "description": c.get("description", ""),
                                "school": c.get("school", ""),
                                "enrollment_reqs": c.get("enrollment_reqs", ""),
                                "prerequisites": [],
                            }
        except Exception:
            pass
        return {"error": f"Course {code} not found"}

    return {
        "code": info.code,
        "name": info.title,
        "credits": info.credits,
        "description": info.description,
        "school": info.school,
        "enrollment_reqs": info.enrollment_reqs,
        "prerequisites": store.get_prerequisites(code),
    }


@router.get("/{course_code}/professor")
async def get_professor_for_course(course_code: str):
    """
    Get the best professor for a course based on A-rate.

    Args:
        course_code: Course code (e.g., "CS 3345", "CS+3345", or "CS%203345")

    Returns:
        {professor, a_rate, total_students, display} or {professor: None}
    """
    # Parse course code - handle various formats
    code = course_code.replace("+", " ").replace("-", " ").strip()
    parts = code.split()

    if len(parts) < 2:
        raise HTTPException(
            status_code=400,
            detail="Invalid course code format. Use 'CS 3345' or 'CS+3345'"
        )

    subject = parts[0].upper()
    number = parts[1]

    result = await nebula.get_best_professor(subject, number)

    if not result:
        return {"professor": None, "a_rate": None}

    return {
        "professor": result["name"],
        "a_rate": result["a_rate"],
        "total_students": result["total_students"],
        "display": f"{result['name']} ({result['a_rate']}% A-rate)",
    }


class BulkProfessorRequest(BaseModel):
    course_codes: list[str]  # e.g., ["CS 3345", "MATH 2418", "PHYS 2326"]


@router.post("/bulk-professors")
async def get_bulk_professors(request: BulkProfessorRequest):
    """
    Get best professors for multiple courses in a single request.
    Much faster than making individual requests for each course.

    Returns:
        {results: {course_code: {professor, a_rate, total_students, display} | null}}
    """
    async def fetch_prof(code: str):
        parts = code.replace("+", " ").replace("-", " ").strip().split()
        if len(parts) < 2:
            return code, None
        result = await nebula.get_best_professor(parts[0].upper(), parts[1])
        if result:
            return code, {
                "professor": result["name"],
                "a_rate": result["a_rate"],
                "total_students": result["total_students"],
                "display": f"{result['name']} ({result['a_rate']}% A-rate)",
            }
        return code, None

    # Fetch all professors in parallel
    tasks = [fetch_prof(code) for code in request.course_codes]
    results = await asyncio.gather(*tasks)

    return {"results": {code: data for code, data in results}}
