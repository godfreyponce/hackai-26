from fastapi import APIRouter, Query
from typing import List, Optional

from models.schemas import Course
from services.nebula import NebulaClient

router = APIRouter()
nebula = NebulaClient()


@router.get("/", response_model=List[Course])
async def list_courses(
    q: Optional[str] = Query(None, description="Search query"),
    department: Optional[str] = Query(None, description="Filter by department"),
    level: Optional[int] = Query(None, description="Filter by course level"),
):
    """List available courses with optional filters."""
    courses = await nebula.get_courses(
        query=q,
        department=department,
        level=level,
    )
    return courses


@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str):
    """Get details for a specific course."""
    course = await nebula.get_course(course_id)
    return course


@router.get("/{course_id}/prerequisites")
async def get_prerequisites(course_id: str):
    """Get prerequisite tree for a course."""
    prereqs = await nebula.get_prerequisites(course_id)
    return prereqs
