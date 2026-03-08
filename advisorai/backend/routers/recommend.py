"""
Recommendation API endpoint.
Author: Sual (recommendation engine scope)

POST /api/recommend - Generate personalized course recommendations

This router orchestrates:
1. Fetching course data from Nebula API
2. Loading degree requirements for the student's major
3. Filtering eligible courses based on prerequisites and requirements
4. Scoring and ranking courses
5. Generating LLM reasoning for recommendations
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from models.schemas import (
    StudentInput,
    RecommendationResponse,
    CourseRecommendation,
    NebulaCourse,
    NebulaProfessor,
)
from services import recommender
from services import llm
from services.nebula import get_all_courses, get_professors_for_courses
from services.transcript_parser import get_degree_requirements

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=RecommendationResponse,
    summary="Generate course recommendations",
    description="Generate personalized course recommendations based on student's completed courses, interests, and constraints.",
    responses={
        200: {"description": "Successful recommendations"},
        422: {"description": "Validation error - required fields missing or invalid"},
        500: {"description": "Internal server error - Nebula API or LLM failure"},
    },
)
async def recommend_courses(student_input: StudentInput) -> RecommendationResponse:
    """
    Generate personalized course recommendations for a student.

    Process:
    1. Fetch all available courses from Nebula API
    2. Load degree requirements for student's major
    3. Filter to eligible courses (prereqs met, not completed, in requirements)
    4. Score and rank courses based on interest match, professor quality, availability
    5. Generate natural-language reasoning using Claude
    6. Return top recommendations with alternative career path suggestions
    """
    logger.info(
        f"Generating recommendations for major={student_input.major}, "
        f"interest={student_input.student_interest}, "
        f"credit_limit={student_input.credit_limit}"
    )

    try:
        # Step 1: Fetch all courses from Nebula API
        all_courses = await _fetch_courses_safe()

        if not all_courses:
            logger.warning("No courses returned from Nebula API")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch course data from Nebula API",
            )

        # Step 2: Load degree requirements and completed courses
        degree_requirements = await _get_requirements_safe(student_input.major)
        course_ids = [c.id for c in all_courses]

        if not degree_requirements:
            logger.warning(f"No degree requirements found for major: {student_input.major}")
            degree_requirements = course_ids

        # Step 3: Get completed course IDs
        completed_course_ids = {
            c.course_id for c in student_input.completed_courses
        }

        # Step 4: Filter eligible courses FIRST (before fetching professors)
        eligible_courses = recommender.filter_eligible_courses(
            all_courses=all_courses,
            completed_course_ids=completed_course_ids,
            degree_requirements=degree_requirements,
        )

        if not eligible_courses:
            logger.info("No eligible courses found after filtering")
            return RecommendationResponse(
                recommended_courses=[],
                alternative_career_paths=[],
            )

        # Step 5: Fetch professor data ONLY for eligible courses
        professors_map = await _fetch_professors_safe(eligible_courses)

        # Step 6: Get top courses for LLM reasoning (pre-scored)
        top_courses_for_llm = recommender.get_top_courses_for_llm(
            eligible_courses=eligible_courses,
            professors_map=professors_map,
            student_interest=student_input.student_interest,
            limit=15,
        )

        # Step 7: Generate reasoning with LLM
        recommendations = await _generate_reasoning_safe(
            student_input=student_input,
            ranked_courses=top_courses_for_llm,
        )

        # Step 8: Merge professor data back into recommendations
        recommendations = llm.merge_professor_data(recommendations, professors_map)

        # Step 9: Apply credit limit and final selection
        final_recommendations = _apply_credit_limit(
            recommendations=recommendations,
            credit_limit=student_input.credit_limit,
        )

        # Step 10: Generate alternative career paths (optional, non-blocking)
        alternative_paths = await _generate_paths_safe(
            completed_courses=list(completed_course_ids),
        )

        logger.info(
            f"Returning {len(final_recommendations)} recommendations "
            f"and {len(alternative_paths)} alternative paths"
        )

        return RecommendationResponse(
            recommended_courses=final_recommendations,
            alternative_career_paths=alternative_paths if alternative_paths else None,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error in recommend_courses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


# ============================================================================
# Helper Functions with Error Handling
# ============================================================================

async def _fetch_courses_safe() -> list[NebulaCourse]:
    """Fetch courses with error handling."""
    try:
        return await get_all_courses()
    except Exception as e:
        logger.error(f"Failed to fetch courses from Nebula: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Nebula API error: {str(e)}",
        )


async def _fetch_professors_safe(
    courses: list[NebulaCourse],
) -> dict[str, list[NebulaProfessor]]:
    """Fetch professors with error handling."""
    try:
        return await get_professors_for_courses(courses)
    except Exception as e:
        logger.warning(f"Failed to fetch professor data: {e}")
        # Return empty map - recommendations will work without professor data
        return {}


async def _get_requirements_safe(major: str) -> list[str]:
    """Get degree requirements with error handling."""
    try:
        return await get_degree_requirements(major)
    except Exception as e:
        logger.warning(f"Failed to load degree requirements for {major}: {e}")
        return []


async def _generate_reasoning_safe(
    student_input: StudentInput,
    ranked_courses: list[dict],
) -> list[CourseRecommendation]:
    """Generate LLM reasoning with error handling."""
    try:
        return await llm.generate_reasoning(
            student_input=student_input,
            ranked_courses=ranked_courses,
        )
    except Exception as e:
        logger.error(f"LLM reasoning generation failed: {e}")
        # Fall back to recommendations without reasoning
        return [
            CourseRecommendation(
                course_id=c["course_id"],
                course_name=c["course_name"],
                credits=c["credits"],
                score=c["score"],
                label="career-aligned" if c.get("interest_match") != "none" else "general-option",
                professor=None,
                reasoning="",  # Empty reasoning as fallback
            )
            for c in ranked_courses[:8]
        ]


async def _generate_paths_safe(
    completed_courses: list[str],
) -> list:
    """Generate alternative paths with error handling."""
    try:
        return await llm.generate_alternative_paths(completed_courses)
    except Exception as e:
        logger.warning(f"Failed to generate alternative paths: {e}")
        return []


def _apply_credit_limit(
    recommendations: list[CourseRecommendation],
    credit_limit: int,
) -> list[CourseRecommendation]:
    """
    Apply credit limit to final recommendations.

    Greedily selects courses by score until credit limit is reached.
    """
    # Sort by score descending (should already be sorted, but ensure)
    sorted_recs = sorted(recommendations, key=lambda x: x.score, reverse=True)

    selected = []
    total_credits = 0

    for rec in sorted_recs:
        if total_credits + rec.credits <= credit_limit:
            selected.append(rec)
            total_credits += rec.credits

        # Max 8 recommendations
        if len(selected) >= 8:
            break

    return selected
