"""
llm.py — Gemini API integration for natural language advisor explanations.

Uses the Gemini API to generate conversational explanations for course
recommendations, tailored to the student's transcript and career goals.
"""

import os
import logging
import json
from typing import Optional

from dotenv import load_dotenv
import httpx

from models.schemas import CourseRecommendation, TranscriptData

logger = logging.getLogger(__name__)

# Load .env file from backend directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


async def generate_advisor_message(
    recommendations: list[CourseRecommendation],
    transcript: TranscriptData,
    career_goal: Optional[str] = None,
) -> str:
    """
    Generate a conversational advisor message explaining the recommendations.

    Uses Gemini to create a natural, encouraging explanation of why
    these courses were selected and how they fit the student's path.
    """
    # Build context for the prompt
    completed_count = len(transcript.completed_courses)
    ip_courses = [c for c in transcript.completed_courses if c.grade == "IP"]

    rec_text = "\n".join([
        f"- {r.course_code}: {r.course_name} "
        f"(confidence: {r.confidence_score:.0%}"
        f"{', uncertainty: ' + r.uncertainty_type.value if r.uncertainty_type else ''})"
        f" — {r.reason}"
        for r in recommendations
    ])

    total_rec_credits = sum(3 for _ in recommendations)  # Estimate

    prompt = f"""You are AdvisorAI, a friendly and knowledgeable academic advisor at UT Dallas.
A student has uploaded their transcript and is looking for course recommendations for next semester.

STUDENT PROFILE:
- Name: {transcript.student_name}
- Major: {transcript.major}
- GPA: {transcript.gpa}
- Total Credit Hours: {transcript.total_credit_hours}
- Courses Completed: {completed_count}
- Currently Taking: {len(ip_courses)} courses
{f'- Career Interest: {career_goal}' if career_goal else ''}

RECOMMENDED COURSES FOR NEXT SEMESTER:
{rec_text}

Total recommended credits: ~{total_rec_credits}

INSTRUCTIONS:
1. Greet the student by name warmly
2. Briefly acknowledge their academic progress (GPA, credits completed)
3. Explain each recommended course in 1-2 sentences — WHY it's recommended, not just what it is
4. If any courses have uncertainty, explain what that means in plain language:
   - Epistemic uncertainty: "We don't have enough data to be fully confident about this one, but..."
   - Aleatoric uncertainty: "This is a great choice, though there are other equally valid options..."
5. Give one piece of overall semester advice
6. Keep it conversational and encouraging — this should sound like talking to a real advisor
7. Keep the total response under 250 words

Do NOT use markdown formatting. Write in plain conversational text suitable for text-to-speech."""

    try:
        response = await call_gemini(prompt)
        return response
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        # Fallback: generate a simple message without LLM
        return _fallback_message(recommendations, transcript, career_goal)


async def process_voice_query(
    transcription: str,
    transcript: Optional[TranscriptData] = None,
) -> str:
    """
    Process a voice query from a student and generate an advisor response.
    """
    context = ""
    if transcript:
        context = f"""
STUDENT CONTEXT:
- Name: {transcript.student_name}
- Major: {transcript.major}
- GPA: {transcript.gpa}
- Credits: {transcript.total_credit_hours}
"""

    prompt = f"""You are AdvisorAI, a friendly academic advisor at UT Dallas.
A student has asked you the following question by voice:

"{transcription}"
{context}
Provide a helpful, conversational response that:
1. Directly addresses their question
2. Offers relevant advice or information
3. Suggests next steps if appropriate

Keep the response concise (under 150 words) and natural for text-to-speech playback.
Do NOT use markdown formatting."""

    try:
        response = await call_gemini(prompt)
        return response
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return "I'm having trouble connecting right now. Please try again in a moment."


async def call_gemini(prompt: str) -> str:
    """Make a request to the Gemini API."""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, using fallback response")
        return "[Gemini API key not configured. Set GEMINI_API_KEY environment variable.]"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                    "topP": 0.9,
                }
            },
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        # Extract text from Gemini response format
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")

        return "I wasn't able to generate a response. Please try again."


def _fallback_message(
    recommendations: list[CourseRecommendation],
    transcript: TranscriptData,
    career_goal: Optional[str],
) -> str:
    """Generate a simple advisor message without LLM."""
    lines = [
        f"Hi {transcript.student_name}! Based on your transcript "
        f"({transcript.gpa} GPA, {transcript.total_credit_hours} hours completed), "
        f"here are my recommendations for next semester:",
        "",
    ]

    for rec in recommendations:
        uncertainty_note = ""
        if rec.uncertainty_type == "epistemic":
            uncertainty_note = " (note: limited data available for this recommendation)"
        elif rec.uncertainty_type == "aleatoric":
            uncertainty_note = " (note: equally good alternatives exist)"

        lines.append(f"• {rec.course_code}: {rec.course_name}{uncertainty_note}")
        lines.append(f"  → {rec.reason}")
        lines.append("")

    if career_goal:
        lines.append(f"These selections are aligned with your interest in {career_goal}.")

    lines.append("Good luck next semester! Let me know if you have any questions.")

    return "\n".join(lines)
