"""
Pydantic schemas for AdvisorAI recommendation engine.
Author: Sual (recommendation engine scope)
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


# ============================================================================
# Nebula API Data Models (representing external API responses)
# ============================================================================

class NebulaSection(BaseModel):
    """Section data from Nebula Labs API."""
    id: str
    days: list[str]  # e.g., ["Monday", "Wednesday", "Friday"]
    start_time: str  # e.g., "10:00"
    end_time: str    # e.g., "11:15"
    professor_id: str
    available_seats: Optional[int] = None  # None if unknown
    total_seats: Optional[int] = None


class NebulaProfessor(BaseModel):
    """Professor data from Nebula Labs API."""
    id: str
    name: str
    avg_grade: float = Field(ge=0.0, le=4.0)  # GPA scale
    grade_consistency: float = Field(ge=0.0, le=1.0)  # 0 = inconsistent, 1 = very consistent


class NebulaCourse(BaseModel):
    """Course data from Nebula Labs API."""
    id: str  # e.g., "CS 2340" (human-readable)
    nebula_id: str = ""  # MongoDB ObjectID used for Nebula API calls
    name: str
    prereqs: list[str] = []  # List of course IDs
    credits: int = Field(ge=1, le=6)
    sections: list[NebulaSection] = []
    professors: list[str] = []  # List of professor IDs teaching this course


# ============================================================================
# Student Input Models
# ============================================================================

class CompletedCourse(BaseModel):
    """A course the student has already completed."""
    course_id: str  # e.g., "CS 1337"
    course_name: str
    grade: str  # e.g., "A", "B+", "C"
    credits: int


class StudentInput(BaseModel):
    """Input from the student for generating recommendations."""
    completed_courses: list[CompletedCourse]
    student_interest: Optional[str] = None  # e.g., "machine learning", "cybersecurity"
    credit_limit: int = Field(default=15, ge=1, le=21)
    scheduling_preference: Optional[str] = None  # e.g., "morning classes", "no Friday"
    major: str  # e.g., "Computer Science"


# ============================================================================
# Recommendation Output Models
# ============================================================================

class RecommendationLabel(str, Enum):
    """Label indicating why a course was recommended."""
    CAREER_ALIGNED = "career-aligned"
    GENERAL_OPTION = "general-option"


class ProfessorRecommendation(BaseModel):
    """Recommended professor for a course."""
    professor_id: str
    professor_name: str
    avg_grade: float
    consistency_score: float


class CourseRecommendation(BaseModel):
    """A single course recommendation with scoring and reasoning."""
    course_id: str
    course_name: str
    credits: int
    score: float = Field(ge=0.0, le=1.0)
    label: Literal["career-aligned", "general-option"]
    professor: Optional[ProfessorRecommendation] = None
    reasoning: str = ""  # Populated by LLM


class AlternativeCareerPath(BaseModel):
    """AI-suggested career path based on completed courses."""
    career: str
    reasoning: str


class RecommendationResponse(BaseModel):
    """Full response from the recommendation endpoint."""
    recommended_courses: list[CourseRecommendation]
    alternative_career_paths: Optional[list[AlternativeCareerPath]] = None
