"""
Recommend router — POST /api/recommend

Orchestrates the full pipeline:
transcript → recommender → Gemini LLM → SemesterPlan JSON
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from pydantic import BaseModel

from models.schemas import (
    TranscriptData,
    SemesterPlan,
    CourseRecommendation,
)
from services.transcript_parser import TranscriptParser
from services.recommender import generate_recommendations
from services.llm import generate_advisor_message, generate_full_plan
from services.data_loader import get_course_store

router = APIRouter()
parser = TranscriptParser()


@router.post("/", response_model=SemesterPlan)
async def recommend_from_transcript(
    file: UploadFile = File(...),
    career_goal: Optional[str] = Form(None),
    credits_per_semester: int = Form(15),
):
    """
    Upload transcript + career goal → get a full semester plan.

    Accepts:
    - file: UTD unofficial transcript PDF
    - career_goal: Student's career interest (optional)
    - credits_per_semester: Target credit load (default 15)

    Returns:
    - SemesterPlan with ranked recommendations, confidence scores,
      uncertainty labels, and a natural language advisor message.
    """
    # Step 1: Parse transcript
    if not file.filename or not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Please upload a PDF or TXT transcript.")

    try:
        content = await file.read()
        transcript = parser.parse(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse transcript: {e}")

    # Step 2: Generate recommendations
    try:
        recommendations = generate_recommendations(
            transcript=transcript,
            career_goal=career_goal,
            credits_per_semester=credits_per_semester,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")

    # Step 3: Generate advisor message via Gemini
    try:
        advisor_message = await generate_advisor_message(
            recommendations=recommendations,
            transcript=transcript,
            career_goal=career_goal,
        )
    except Exception as e:
        # Don't fail the whole request if LLM fails
        advisor_message = f"Here are your recommended courses for next semester based on your {transcript.major} degree progress."

    # Step 4: Return semester plan
    store = get_course_store()
    total_credits = sum(
        (store.get_course(r.course_code).credits if store.get_course(r.course_code) else 3)
        for r in recommendations
    )

    return SemesterPlan(
        recommendations=recommendations,
        advisor_message=advisor_message,
        total_credits=float(total_credits),
        semester="2026 Fall",  # Next semester
    )


@router.post("/from-data", response_model=SemesterPlan)
async def recommend_from_data(transcript: TranscriptData, career_goal: Optional[str] = None):
    """
    Alternative endpoint: accept pre-parsed TranscriptData JSON directly.
    Useful when the frontend has already parsed the transcript.
    """
    recommendations = generate_recommendations(
        transcript=transcript,
        career_goal=career_goal,
    )

    advisor_message = await generate_advisor_message(
        recommendations=recommendations,
        transcript=transcript,
        career_goal=career_goal,
    )

    store = get_course_store()
    total_credits = sum(
        (store.get_course(r.course_code).credits if store.get_course(r.course_code) else 3)
        for r in recommendations
    )

    return SemesterPlan(
        recommendations=recommendations,
        advisor_message=advisor_message,
        total_credits=float(total_credits),
        semester="2026 Fall",
    )


@router.get("/{student_id}")
async def get_recommendations(student_id: str):
    """Placeholder for fetching saved recommendations by student ID."""
    return {"student_id": student_id, "recommendations": [], "message": "Upload your transcript to get recommendations."}


# ─── Full 4-Year Plan ─────────────────────────────────────────────

class FullPlanRequest(BaseModel):
    transcript_context: str
    career_goal: Optional[str] = None
    current_semester: str = "Fall 2026"
    total_credit_hours: float = 0.0
    gpa: Optional[float] = None
    target_graduation: Optional[str] = None  # e.g. "Spring 2027" for early graduation requests
    start_semester: Optional[str] = None     # e.g. "Fall 2024" — when student started college
    major: Optional[str] = None              # e.g. "Computer Science"
    completed_courses: Optional[list[str]] = None  # List of completed course codes


@router.post("/full-plan")
async def generate_full_degree_plan(request: FullPlanRequest):
    """
    Generate a complete multi-semester degree plan using Gemini.

    POST body:
    - transcript_context: Full transcript summary string
    - career_goal: Optional career interest
    - current_semester: e.g. "Fall 2026"
    - total_credit_hours: Credits completed so far
    - gpa: Student's cumulative GPA (optional)
    - target_graduation: Optional target grad date
    - start_semester: When student started college (to compute 4-year grad)
    - major: Student's major for degree plan lookup
    - completed_courses: List of completed course codes

    Returns:
    - {semesters: [{semester, courses: [{code, title, credits, reason}], total_credits}],
       graduation_semester, total_semesters}
    """
    try:
        plan = await generate_full_plan(
            transcript_context=request.transcript_context,
            career_goal=request.career_goal,
            current_semester=request.current_semester,
            total_credit_hours=request.total_credit_hours,
            gpa=request.gpa,
            target_graduation=request.target_graduation,
            start_semester=request.start_semester,
            major=request.major,
            completed_courses=request.completed_courses,
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate degree plan: {e}")
