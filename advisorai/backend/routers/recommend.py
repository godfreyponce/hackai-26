# SUALS PART
from fastapi import APIRouter, HTTPException
from typing import List

from models.schemas import RecommendationRequest, RecommendationResponse, Course
from services.recommender import get_course_recommendations
from services.llm import generate_recommendation_reasoning

router = APIRouter()


@router.post("/", response_model=RecommendationResponse)
async def recommend_courses(request: RecommendationRequest):
    """Generate personalized course recommendations."""
    try:
        # Get scored recommendations
        recommendations = await get_course_recommendations(
            student_id=request.student_id,
            completed_courses=request.completed_courses,
            preferences=request.preferences,
        )

        # Generate LLM reasoning for recommendations
        reasoning = await generate_recommendation_reasoning(
            recommendations=recommendations,
            student_context=request.dict(),
        )

        return RecommendationResponse(
            courses=recommendations,
            reasoning=reasoning,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{student_id}")
async def get_recommendations(student_id: str):
    """Get recommendations for a specific student."""
    # TODO: Fetch student data and generate recommendations
    return {"student_id": student_id, "recommendations": []}
