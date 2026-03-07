# SUALS PART: scoring & course selection
from typing import List, Dict, Any, Optional

from models.schemas import Course, StudentPreferences
from services.nebula import NebulaClient

nebula = NebulaClient()


async def get_course_recommendations(
    student_id: str,
    completed_courses: List[str],
    preferences: Optional[StudentPreferences] = None,
) -> List[Course]:
    """
    Generate course recommendations based on student history and preferences.

    Scoring factors:
    - Prerequisite satisfaction
    - Degree requirement progress
    - Student preferences (time, difficulty, interests)
    - Course availability
    """
    # Fetch available courses
    all_courses = await nebula.get_courses()

    # Filter out completed courses
    available_courses = [
        c for c in all_courses
        if c.code not in completed_courses
    ]

    # Score each course
    scored_courses = []
    for course in available_courses:
        score = await calculate_course_score(
            course=course,
            completed=completed_courses,
            preferences=preferences,
        )
        scored_courses.append((course, score))

    # Sort by score and return top recommendations
    scored_courses.sort(key=lambda x: x[1], reverse=True)

    return [course for course, _ in scored_courses[:10]]


async def calculate_course_score(
    course: Course,
    completed: List[str],
    preferences: Optional[StudentPreferences],
) -> float:
    """Calculate recommendation score for a course."""
    score = 0.0

    # Check prerequisites are met
    prereqs_met = check_prerequisites(course, completed)
    if not prereqs_met:
        return -1.0  # Cannot take this course

    # Base score from degree requirements
    score += get_requirement_score(course)

    # Preference matching
    if preferences:
        score += match_preferences(course, preferences)

    return score


def check_prerequisites(course: Course, completed: List[str]) -> bool:
    """Check if all prerequisites are satisfied."""
    # TODO: Implement prerequisite checking logic
    return True


def get_requirement_score(course: Course) -> float:
    """Score based on how course contributes to degree requirements."""
    # TODO: Implement degree requirement scoring
    return 1.0


def match_preferences(course: Course, preferences: StudentPreferences) -> float:
    """Score based on preference matching."""
    score = 0.0

    # Interest matching
    if preferences.interests:
        # TODO: Implement interest matching with course topics
        pass

    # Time preference matching
    if preferences.preferred_times:
        # TODO: Check course schedule against preferred times
        pass

    # Difficulty preference
    if preferences.max_difficulty:
        # TODO: Compare course difficulty rating
        pass

    return score
