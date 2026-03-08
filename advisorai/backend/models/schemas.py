from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class NebulaSection(BaseModel):
    """A section fetched from the Nebula Labs API."""
    id: str
    days: List[str] = []
    start_time: str = ""
    end_time: str = ""
    professor_id: str = ""
    available_seats: Optional[int] = None
    total_seats: Optional[int] = None


class NebulaProfessor(BaseModel):
    """A professor fetched from the Nebula Labs API with computed grade stats."""
    id: str
    name: str
    avg_grade: float = 3.0
    grade_consistency: float = 0.5


class NebulaCourse(BaseModel):
    """A course fetched from the Nebula Labs API."""
    id: str
    nebula_id: str = ""
    name: str
    prereqs: List[str] = []
    credits: int = 3
    sections: List[NebulaSection] = []
    professors: List[NebulaProfessor] = []


class Course(BaseModel):
    """Course model."""
    id: Optional[str] = None
    code: str
    name: str
    credits: int
    description: Optional[str] = None
    department: Optional[str] = None
    level: Optional[int] = None
    prerequisites: Optional[List[str]] = None


class StudentPreferences(BaseModel):
    """Student preferences for course recommendations."""
    interests: Optional[List[str]] = None
    preferred_times: Optional[List[str]] = None  # e.g., ["morning", "afternoon"]
    max_difficulty: Optional[int] = None  # 1-5 scale
    max_credits: Optional[int] = None
    avoid_professors: Optional[List[str]] = None


class RecommendationRequest(BaseModel):
    """Request for course recommendations."""
    student_id: str
    completed_courses: List[str]
    preferences: Optional[StudentPreferences] = None
    target_semester: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response containing course recommendations."""
    courses: List[Course]
    reasoning: str


class CompletedCourse(BaseModel):
    """A single completed course from a student's transcript."""
    course_code: str          # e.g. "CS 1337"
    course_name: str          # e.g. "Computer Science I"
    grade: str                # e.g. "A", "B+", "W", "CR"
    credit_hours: float = 3.0  # e.g. 3.0 (optional, defaults to 3)
    semester: Optional[str] = None  # e.g. "2024 Fall"


class UncertaintyType(str, Enum):
    """Type of uncertainty in a recommendation."""
    EPISTEMIC = "epistemic"    # Not enough data to be confident
    ALEATORIC = "aleatoric"    # Genuinely ambiguous decision


class TranscriptData(BaseModel):
    """Fully parsed UTD unofficial transcript."""
    student_name: str
    student_id: Optional[str] = None
    major: str
    total_credit_hours: float
    minor: Optional[str] = None
    gpa: float
    completed_courses: List[CompletedCourse]


class CourseRecommendation(BaseModel):
    """A single course recommendation with confidence and reasoning."""
    course_code: str
    course_name: str
    reason: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    uncertainty_type: Optional[UncertaintyType] = None
    professor_suggestion: Optional[str] = None
    average_gpa: Optional[float] = None


class SemesterPlan(BaseModel):
    """Full semester plan returned to the student."""
    recommendations: List[CourseRecommendation]
    advisor_message: str
    total_credits: float
    semester: Optional[str] = None
