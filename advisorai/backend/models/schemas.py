from pydantic import BaseModel
from typing import List, Optional


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


class TranscriptData(BaseModel):
    """Parsed transcript data."""
    courses: List[dict]
    gpa: Optional[float] = None
    total_credits: float
