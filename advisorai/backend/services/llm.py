"""
Gemini LLM integration for generating course reasoning and advisor chat.
Author: Sual (recommendation engine scope)

Uses Google Generative AI SDK with gemini-2.0-flash model.
API key loaded from environment variable GOOGLE_API_KEY.

Design Decisions:
- Reasoning generation returns structured JSON, parsed and merged with CourseRecommendation
- Chat maintains conversation history for multi-turn interactions
- Alternative paths are clearly labeled as AI suggestions
- All prompts emphasize respecting student's stated interest above assumptions
"""

import asyncio
import json
import logging
import os
from typing import Optional

from google import genai
from google.genai import types

from models.schemas import (
    StudentInput,
    CourseRecommendation,
    AlternativeCareerPath,
)

logger = logging.getLogger(__name__)

# Initialize Gemini client
# API key loaded from environment variable GOOGLE_API_KEY
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", ""))

MODEL = "gemini-2.5-flash"


# ============================================================================
# System Prompts
# ============================================================================

REASONING_SYSTEM_PROMPT = """You are an academic advising AI. Your task is to generate concise, friendly, natural-language reasoning for each course recommendation based on the student's input.

Rules:
1. Weight the student's stated interest HIGHEST. Never override it with assumptions.
2. If student_interest is null, label recommendations as general options and explain based on degree progress.
3. For each course, explain: why it fits their goal, why the professor is recommended, and any prerequisite context.
4. Keep each reasoning string under 3 sentences.
5. Do NOT assume a career goal the student didn't provide.
6. Return ONLY valid JSON. No markdown. No preamble. No explanation outside the JSON.

Return this exact format:
{
  "courses": [
    {
      "course_id": "...",
      "reasoning": "..."
    }
  ],
  "alternative_career_paths": [
    {
      "career": "...",
      "reasoning": "..."
    }
  ]
}"""

CHAT_SYSTEM_PROMPT = """You are a friendly UTD academic advisor. Ask clarifying questions about the student's goals, course load preferences, and career interests. Keep responses concise and conversational.

Guidelines:
- Be warm and supportive
- Ask one question at a time
- Reference UTD-specific programs when relevant
- If the student seems unsure, offer 2-3 concrete options
- Never make up course names or requirements
- Encourage the student to explore their interests"""

ALTERNATIVE_PATHS_SYSTEM_PROMPT = """You are a career advisor analyzing a student's completed coursework. Based on the courses they've taken, suggest 2-3 career paths that align well with their academic background.

Guidelines:
- Only suggest paths that genuinely connect to their completed courses
- Be specific about which courses support each path
- Keep reasoning to 2-3 sentences per path
- Label these clearly as suggestions, not guarantees
- Return ONLY valid JSON with no markdown or preamble

Return format:
{
  "paths": [
    {
      "career": "...",
      "reasoning": "..."
    }
  ]
}"""


# ============================================================================
# Main Functions
# ============================================================================

async def generate_reasoning(
    student_input: StudentInput,
    ranked_courses: list[dict],
) -> list[CourseRecommendation]:
    """
    Generate natural-language reasoning for course recommendations using Claude.

    Args:
        student_input: The student's input data
        ranked_courses: Top 15 pre-scored courses from recommender.py

    Returns:
        List of CourseRecommendation objects with reasoning populated
    """
    # Build user message with student context and courses
    user_message = json.dumps({
        "student": {
            "major": student_input.major,
            "interest": student_input.student_interest,
            "credit_limit": student_input.credit_limit,
            "scheduling_preference": student_input.scheduling_preference,
            "completed_courses": [
                {"id": c.course_id, "name": c.course_name, "grade": c.grade}
                for c in student_input.completed_courses
            ],
        },
        "recommended_courses": ranked_courses,
    }, indent=2)

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(system_instruction=REASONING_SYSTEM_PROMPT),
        )

        # Extract text content
        response_text = response.text

        # Parse JSON response
        parsed = _parse_llm_json(response_text)

        if not parsed or "courses" not in parsed:
            logger.error(f"Invalid LLM response format: {response_text[:200]}")
            raise ValueError("LLM returned invalid response format")

        # Build reasoning map
        reasoning_map = {
            item["course_id"]: item["reasoning"]
            for item in parsed.get("courses", [])
        }

        # Build CourseRecommendation objects with reasoning
        recommendations = []
        for course_data in ranked_courses[:8]:  # Limit to top 8
            course_id = course_data["course_id"]
            reasoning = reasoning_map.get(course_id, "")

            recommendations.append(
                CourseRecommendation(
                    course_id=course_id,
                    course_name=course_data["course_name"],
                    credits=course_data["credits"],
                    score=course_data["score"],
                    label="career-aligned" if course_data.get("interest_match") != "none" else "general-option",
                    professor=None,  # Will be populated by router from original data
                    reasoning=reasoning,
                )
            )

        logger.info(f"Generated reasoning for {len(recommendations)} courses")
        return recommendations

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError(f"LLM response was not valid JSON: {e}")


async def chat_with_advisor(
    conversation_history: list[dict],
    user_message: str,
) -> str:
    """
    Conduct a multi-turn conversation with the AI academic advisor.

    Args:
        conversation_history: List of previous messages [{role, content}, ...]
        user_message: The new message from the user

    Returns:
        Assistant's response text
    """
    # Convert history to Gemini Content format using typed objects
    gemini_history = []
    for msg in conversation_history:
        role = "model" if msg["role"] in ("assistant", "model") else "user"
        gemini_history.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            )
        )

    # Append the new user message
    gemini_history.append(
        types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        )
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=gemini_history,
            config=types.GenerateContentConfig(system_instruction=CHAT_SYSTEM_PROMPT),
        )

        assistant_response = response.text

        logger.info(f"Chat response generated ({len(assistant_response)} chars)")
        return assistant_response

    except Exception as e:
        logger.error(f"Gemini API error in chat: {e}")
        raise


async def generate_alternative_paths(
    completed_courses: list[str],
) -> list[AlternativeCareerPath]:
    """
    Generate alternative career path suggestions based on completed courses.

    Args:
        completed_courses: List of completed course IDs

    Returns:
        List of AlternativeCareerPath objects (2-3 suggestions)
    """
    if not completed_courses:
        return []

    user_message = json.dumps({
        "completed_course_ids": completed_courses,
        "instructions": "Based on these completed courses, suggest 2-3 career paths that align well.",
    })

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(system_instruction=ALTERNATIVE_PATHS_SYSTEM_PROMPT),
        )

        response_text = response.text
        parsed = _parse_llm_json(response_text)

        if not parsed or "paths" not in parsed:
            logger.warning(f"Invalid paths response: {response_text[:200]}")
            return []

        paths = [
            AlternativeCareerPath(
                career=item["career"],
                reasoning=item["reasoning"],
            )
            for item in parsed.get("paths", [])
        ]

        logger.info(f"Generated {len(paths)} alternative career paths")
        return paths

    except Exception as e:
        logger.error(f"Gemini API error generating paths: {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse alternative paths: {e}")
        return []


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_llm_json(response_text: str) -> Optional[dict]:
    """
    Parse JSON from LLM response, handling potential formatting issues.

    Attempts to extract JSON even if there's extra text around it.
    """
    text = response_text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in response
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1

    if start_idx != -1 and end_idx > start_idx:
        try:
            return json.loads(text[start_idx:end_idx])
        except json.JSONDecodeError:
            pass

    return None


def merge_professor_data(
    recommendations: list[CourseRecommendation],
    professors_map: dict,
) -> list[CourseRecommendation]:
    """
    Merge professor recommendation data back into CourseRecommendation objects.

    This is called after generate_reasoning to add professor data that wasn't
    included in the LLM context.
    """
    from services.recommender import select_best_professor, score_professor
    from models.schemas import ProfessorRecommendation

    for rec in recommendations:
        professors = professors_map.get(rec.course_id, [])
        if professors:
            best = select_best_professor(professors)
            if best:
                rec.professor = ProfessorRecommendation(
                    professor_id=best.id,
                    professor_name=best.name,
                    avg_grade=best.avg_grade,
                    consistency_score=best.grade_consistency,
                )

    return recommendations
