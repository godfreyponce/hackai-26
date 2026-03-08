"""
Course recommendation scoring and filtering engine.
Author: Sual (recommendation engine scope)

Scoring Formula:
    score = 0.5 * student_priority + 0.3 * professor_rating + 0.2 * availability_score

Design Decisions:
- If student_interest is None, student_priority defaults to 0.0 for all courses
- Partial keyword matching uses simple substring search (case-insensitive)
- Courses with unmet prerequisites are completely filtered out
- Credit limit is enforced greedily (best courses first)
"""

import logging
from typing import Optional

from models.schemas import (
    NebulaCourse,
    NebulaProfessor,
    NebulaSection,
    CourseRecommendation,
    ProfessorRecommendation,
)

logger = logging.getLogger(__name__)

# Scoring weights
WEIGHT_STUDENT_PRIORITY = 0.5
WEIGHT_PROFESSOR_RATING = 0.3
WEIGHT_AVAILABILITY = 0.2

# Keywords commonly associated with CS career interests
# Used for partial matching when exact match fails
INTEREST_KEYWORDS = {
    "machine learning": ["ml", "ai", "data", "neural", "deep learning", "artificial intelligence"],
    "cybersecurity": ["security", "crypto", "network", "malware", "penetration", "ethical hacking"],
    "web development": ["web", "frontend", "backend", "fullstack", "javascript", "react"],
    "data science": ["data", "statistics", "analytics", "visualization", "pandas", "python"],
    "systems": ["operating systems", "os", "low-level", "kernel", "embedded"],
    "software engineering": ["software", "agile", "testing", "devops", "architecture"],
    "game development": ["game", "graphics", "unity", "unreal", "3d"],
}


def filter_eligible_courses(
    all_courses: list[NebulaCourse],
    completed_course_ids: set[str],
    degree_requirements: list[str],
) -> list[NebulaCourse]:
    """
    Filter courses to only those the student can take.

    Filters:
    1. Remove already-completed courses
    2. Remove courses where prerequisites are not fully met
    3. Only keep courses in remaining degree requirements

    Args:
        all_courses: All available courses from Nebula API
        completed_course_ids: Set of course IDs the student has completed
        degree_requirements: List of course IDs required for the student's degree

    Returns:
        List of eligible NebulaCourse objects
    """
    eligible = []
    remaining_requirements = set(degree_requirements) - completed_course_ids

    for course in all_courses:
        # Skip if already completed
        if course.id in completed_course_ids:
            continue

        # Skip if not in degree requirements
        if course.id not in remaining_requirements:
            continue

        # Note: Prereq check is lenient because Nebula's nested CollectionRequirement
        # structure has OR branches that _parse_prereqs flattens to AND (conservative).
        # With partial transcript data, strict checking filters everything out.
        # The LLM handles prereq reasoning in its response.
        # TODO: Implement proper OR/AND prereq tree evaluation

        eligible.append(course)

    logger.info(f"Filtered {len(all_courses)} courses to {len(eligible)} eligible courses")
    return eligible


def _prerequisites_met(prereqs: list[str], completed: set[str]) -> bool:
    """Check if all prerequisites are satisfied."""
    # Handle empty prereqs
    if not prereqs:
        return True

    # All prereqs must be in completed courses
    return all(prereq in completed for prereq in prereqs)


def score_professor(professor: NebulaProfessor) -> float:
    """
    Calculate a normalized score for a professor.

    Combines:
    - avg_grade: Normalized from 0-4 scale to 0-1 (higher is better)
    - grade_consistency: Already 0-1 (higher means more predictable grading)

    Formula: 0.6 * normalized_grade + 0.4 * consistency

    Returns:
        Float score between 0.0 and 1.0
    """
    # Normalize avg_grade from 0-4 to 0-1
    normalized_grade = professor.avg_grade / 4.0

    # Consistency is already 0-1
    consistency = professor.grade_consistency

    # Weighted combination: favor higher grades slightly more
    score = 0.6 * normalized_grade + 0.4 * consistency

    return round(score, 4)


def select_best_professor(
    professors: list[NebulaProfessor],
) -> Optional[NebulaProfessor]:
    """
    Select the professor with the highest score.

    Returns:
        Best professor, or None if list is empty
    """
    if not professors:
        return None

    return max(professors, key=score_professor)


def _calculate_availability_score(sections: list[NebulaSection]) -> float:
    """
    Calculate availability score based on section data.

    - 1.0: Multiple sections with available seats
    - 0.5: Limited availability (1 section or most sections full)
    - 0.0: No sections or all sections full
    """
    if not sections:
        return 0.0

    # Count sections with available seats
    available_sections = 0
    for section in sections:
        if section.available_seats is None:
            # Unknown availability - assume available
            available_sections += 1
        elif section.available_seats > 0:
            available_sections += 1

    if available_sections == 0:
        return 0.0
    elif available_sections == 1:
        return 0.5
    else:
        return 1.0


def _match_student_interest(
    course: NebulaCourse,
    student_interest: Optional[str],
) -> float:
    """
    Calculate how well a course matches the student's stated interest.

    Returns:
    - 1.0: Strong match (course name contains interest keyword)
    - 0.5: Partial match (related keywords found)
    - 0.0: No match or no interest provided
    """
    if not student_interest:
        return 0.0

    interest_lower = student_interest.lower()
    course_name_lower = course.name.lower()
    course_id_lower = course.id.lower()

    # Check for direct match
    if interest_lower in course_name_lower:
        return 1.0

    # Check interest keywords in course name
    interest_words = interest_lower.split()
    for word in interest_words:
        if len(word) > 2 and word in course_name_lower:
            return 1.0

    # Check related keywords
    related_keywords = INTEREST_KEYWORDS.get(interest_lower, [])
    for keyword in related_keywords:
        if keyword in course_name_lower:
            return 0.5

    # Check if any interest word partially matches
    for word in interest_words:
        if len(word) > 3:
            for course_word in course_name_lower.split():
                if word in course_word or course_word in word:
                    return 0.5

    return 0.0


def score_course(
    course: NebulaCourse,
    student_interest: Optional[str],
    best_professor: Optional[NebulaProfessor],
    sections: list[NebulaSection],
) -> float:
    """
    Calculate overall recommendation score for a course.

    Formula: 0.5 * student_priority + 0.3 * professor_rating + 0.2 * availability_score

    Args:
        course: The course to score
        student_interest: Student's stated career interest (may be None)
        best_professor: Best professor for this course (may be None)
        sections: Available sections for this course

    Returns:
        Float score between 0.0 and 1.0
    """
    # Student priority based on interest matching
    student_priority = _match_student_interest(course, student_interest)

    # Professor rating (default to 0.5 if no professor data)
    if best_professor:
        professor_rating = score_professor(best_professor)
    else:
        professor_rating = 0.5

    # Availability score
    availability_score = _calculate_availability_score(sections)

    # Apply weighted formula
    score = (
        WEIGHT_STUDENT_PRIORITY * student_priority +
        WEIGHT_PROFESSOR_RATING * professor_rating +
        WEIGHT_AVAILABILITY * availability_score
    )

    return round(score, 4)


def rank_courses(
    eligible_courses: list[NebulaCourse],
    professors_map: dict[str, list[NebulaProfessor]],
    student_interest: Optional[str],
    credit_limit: int,
) -> list[CourseRecommendation]:
    """
    Rank eligible courses and select top recommendations within credit limit.

    Process:
    1. Score all eligible courses
    2. Sort descending by score
    3. Greedily select courses until credit_limit is reached
    4. Label each course as "career-aligned" or "general-option"

    Args:
        eligible_courses: Courses the student can take
        professors_map: Dict mapping course_id to list of professors
        student_interest: Student's career interest (may be None)
        credit_limit: Maximum total credits to recommend

    Returns:
        List of up to 8 CourseRecommendation objects
    """
    scored_courses = []

    for course in eligible_courses:
        # Get professors for this course
        professors = professors_map.get(course.id, [])
        best_prof = select_best_professor(professors)

        # Calculate score
        score = score_course(
            course=course,
            student_interest=student_interest,
            best_professor=best_prof,
            sections=course.sections,
        )

        # Determine label based on interest match
        interest_match = _match_student_interest(course, student_interest)
        label = "career-aligned" if interest_match > 0 else "general-option"

        # Build professor recommendation if available
        prof_rec = None
        if best_prof:
            prof_rec = ProfessorRecommendation(
                professor_id=best_prof.id,
                professor_name=best_prof.name,
                avg_grade=best_prof.avg_grade,
                consistency_score=best_prof.grade_consistency,
            )

        scored_courses.append({
            "course": course,
            "score": score,
            "label": label,
            "professor": prof_rec,
        })

    # Sort by score descending
    scored_courses.sort(key=lambda x: x["score"], reverse=True)

    # Greedy selection within credit limit
    selected = []
    total_credits = 0

    for item in scored_courses:
        course = item["course"]
        if total_credits + course.credits <= credit_limit:
            total_credits += course.credits
            selected.append(
                CourseRecommendation(
                    course_id=course.id,
                    course_name=course.name,
                    credits=course.credits,
                    score=item["score"],
                    label=item["label"],
                    professor=item["professor"],
                    reasoning="",  # Will be populated by LLM
                )
            )

        # Max 8 recommendations
        if len(selected) >= 8:
            break

    logger.info(
        f"Selected {len(selected)} courses totaling {total_credits} credits "
        f"(limit: {credit_limit})"
    )

    return selected


def get_top_courses_for_llm(
    eligible_courses: list[NebulaCourse],
    professors_map: dict[str, list[NebulaProfessor]],
    student_interest: Optional[str],
    limit: int = 15,
) -> list[dict]:
    """
    Get top scored courses formatted for LLM input.

    Unlike rank_courses, this doesn't apply credit limit and returns
    raw data for the LLM to reason about.

    Returns:
        List of course dicts with scoring info (top 15 by default)
    """
    scored = []

    for course in eligible_courses:
        professors = professors_map.get(course.id, [])
        best_prof = select_best_professor(professors)

        score = score_course(
            course=course,
            student_interest=student_interest,
            best_professor=best_prof,
            sections=course.sections,
        )

        interest_match = _match_student_interest(course, student_interest)

        scored.append({
            "course_id": course.id,
            "course_name": course.name,
            "credits": course.credits,
            "score": score,
            "interest_match": "strong" if interest_match == 1.0 else "partial" if interest_match == 0.5 else "none",
            "best_professor": best_prof.name if best_prof else None,
            "professor_avg_grade": best_prof.avg_grade if best_prof else None,
            "available_sections": len(course.sections),
        })

    # Sort and return top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
