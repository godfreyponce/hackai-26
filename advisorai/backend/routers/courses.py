"""
Courses router — GET /api/courses

Search and browse UTD course catalog from Nebula data.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from services.data_loader import get_course_store
from services import nebula

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


@router.get("/{course_code}")
async def get_course(course_code: str):
    """Get details for a specific course (e.g., CS+1337)."""
    # URL-encode spaces as + in the path
    code = course_code.replace("+", " ").upper()
    store = get_course_store()
    info = store.get_course(code)

    if not info:
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
