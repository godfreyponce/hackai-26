# SUALS PART: Claude prompts & reasoning
import os
from typing import List, Dict, Any
import httpx

from models.schemas import Course

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


async def generate_recommendation_reasoning(
    recommendations: List[Course],
    student_context: Dict[str, Any],
) -> str:
    """
    Generate human-readable reasoning for course recommendations using Claude.
    """
    courses_text = "\n".join([
        f"- {c.code}: {c.name} ({c.credits} credits)"
        for c in recommendations
    ])

    prompt = f"""You are an academic advisor helping a student select courses.

Based on the student's profile and the following recommended courses, provide a brief,
helpful explanation of why these courses are recommended and how they fit into the
student's academic journey.

Student Context:
- Completed courses: {student_context.get('completed_courses', [])}
- Interests: {student_context.get('preferences', {}).get('interests', 'Not specified')}

Recommended Courses:
{courses_text}

Provide a concise, encouraging response (2-3 paragraphs) explaining:
1. Why these courses are a good fit
2. How they progress toward degree completion
3. Any tips for success in these courses"""

    response = await call_claude(prompt)
    return response


async def process_voice_query(transcription: str) -> str:
    """
    Process a voice query from a student and generate an advisor response.
    """
    prompt = f"""You are a friendly, knowledgeable academic advisor at a university.
A student has asked you the following question:

"{transcription}"

Provide a helpful, conversational response that:
1. Directly addresses their question
2. Offers relevant advice or information
3. Suggests next steps if appropriate

Keep the response concise and suitable for text-to-speech playback."""

    response = await call_claude(prompt)
    return response


async def call_claude(prompt: str) -> str:
    """Make a request to the Claude API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]
