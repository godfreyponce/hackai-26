"""
llm.py — Gemini API integration for natural language advisor explanations.

Uses the Gemini API to generate conversational explanations for course
recommendations, tailored to the student's transcript and career goals.
"""

import os
import logging
import json
import asyncio
from typing import Optional

from dotenv import load_dotenv
import httpx
from google import genai
from google.genai import types

from models.schemas import CourseRecommendation, TranscriptData

logger = logging.getLogger(__name__)

# Load .env file from backend directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
MODEL = "gemini-2.5-flash"

# Initialize google-genai client
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

CHAT_SYSTEM_PROMPT = """You are Comet Advisor, a friendly, knowledgeable AI academic advisor at UT Dallas.

Your role:
- Help students plan their courses and understand degree requirements
- Give warm, encouraging advice about academics
- Answer questions about UTD courses, prerequisites, and degree plans
- Help students think through career goals and how courses align

FORMATTING RULES (STRICT):
- NEVER use asterisks, bold (**text**), headers (##), or any markdown. Your text is spoken aloud.
- Use plain text only. For emphasis, use words like "importantly" or "notably" instead of bold.
- Keep responses to 1-2 sentences MAXIMUM. Speak like a text message, not an email.
- Do not repeat what the student just said. Never start with "Great question!", "Sure!", or "Of course!".
- Get straight to the point. No filler phrases. No pleasantries.

ADVISING APPROACH:
- When a student mentions a minor, ALWAYS track it alongside their major going forward.
- When recommending courses or planning semesters, consider BOTH the major AND any mentioned minors.
- Suggest a balanced semester load that makes progress on both programs.
- Proactively mention how many minor courses they still need if you can tell from the data.
- If the student has a minor, their semester plan should include courses for BOTH the major and the minor.

CREDIT HOUR RULES (STRICTLY ENFORCE):
- Fall/Spring semesters: 12-18 credit hours (target: 15 = 5 courses x 3 credits)
- Summer semesters: maximum 9-12 credit hours (3-4 courses)
- NEVER suggest more than 6 courses in any single semester
- If a student asks for more, warn them it requires an academic petition

EARLY GRADUATION REQUESTS:
- If a student asks to "graduate early" or "finish in 3 years", calculate whether it's possible within credit limits
- To graduate early: they would need to take max credits (18/semester) plus summer courses (9-12 each)
- If NOT possible: Be honest and say "Based on your remaining requirements, graduating in X semesters isn't possible without exceeding UTD's credit limits. The fastest realistic plan is Y semesters."
- If POSSIBLE: Suggest the compressed plan but warn about the heavy workload and GPA impact
- NEVER promise what cannot be delivered. Be realistic.

MULTI-DISCIPLINARY COURSES:
- A CS degree requires more than just CS courses. Include MATH, PHYS, ECS, RHET, GOVT courses
- When recommending courses, include ALL required subjects: MATH 2413/2414/2418, PHYS 2325/2326, RHET 1302, GOVT 2305/2306, ECS 2390
- Do not focus only on CS — the student needs a complete degree plan

CONVERSATION FLOW:
- After you've discussed enough to understand the student's major, minor, interests, and goals (usually after 3-4 exchanges), naturally wrap up by suggesting to generate their plan.
- End with something like: "I think we have a great picture of your goals now! Ready to generate your semester plan? Just hit the Generate My Plan button below, or feel free to ask me anything else first."
- Do NOT force this too early. Wait until you've discussed courses, career goals, or semester planning.
- If the student keeps asking questions, keep helping — only suggest the plan when there's a natural pause.

CRITICAL RULES ABOUT COURSE DATA:
- You have access to the OFFICIAL UTD course catalog data including descriptions, prerequisites, and credit hours.
- When courses are provided in the context, that data IS the official catalog. Use it directly and confidently.
- ONLY reference course codes and titles from the data provided to you. NEVER guess or make up course codes.
- NEVER tell students to "check the UTD catalog" or "visit the website" — YOU have the catalog data.
- If a course has prerequisites listed, state them directly and check if the student has completed them.
- If you don't have data for a specific course, say "I don't have that course in my records" rather than redirecting to the catalog."""


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


async def chat_with_advisor(
    conversation_history: list[dict],
    user_message: str,
    transcript_context: Optional[str] = None,
    concise: bool = True,
) -> str:
    """
    Multi-turn conversation with the AI academic advisor via Gemini.

    Args:
        conversation_history: Previous messages [{role: "user"|"model", content: "..."}]
        user_message: The new message from the student
        transcript_context: Summary of the student's parsed transcript
        concise: If True, enforce extra-short responses (1-2 sentences)

    Returns:
        Advisor's response text
    """
    if not client:
        return "I'm not connected right now. Please make sure the Gemini API key is set up."

    # Build system prompt with transcript context
    system_prompt = CHAT_SYSTEM_PROMPT

    # Inject concise mode instructions
    if concise:
        system_prompt += (
            "\n\nCONCISE MODE ACTIVE: Reply in 1-2 sentences MAX. "
            "No pleasantries. No elaboration. Be direct.\n"
            "Good: 'You still need CS 4348 and CS 4349. Want me to add those?'\n"
            "Bad: 'Great question! Based on your transcript, I can see you have completed...'"
        )

    if transcript_context:
        system_prompt += f"\n\nSTUDENT TRANSCRIPT DATA (you have already reviewed this):\n{transcript_context}\n\nIMPORTANT: You have access to this student's transcript. Reference their specific courses, GPA, and progress when relevant. Do NOT say you don't have access to their transcript."

        # Extract GPA from context and inject difficulty guidance
        import re as _re
        gpa_match = _re.search(r"GPA[:\s]+(\d+\.\d+)", transcript_context)
        if gpa_match:
            gpa_val = float(gpa_match.group(1))
            system_prompt += build_gpa_guidance(gpa_val)

    # Convert history to Gemini Content format
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
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )

        assistant_response = response.text or ""
        # Strip markdown formatting Gemini sometimes adds despite instructions
        assistant_response = _strip_markdown(assistant_response)
        logger.info(f"Chat response generated ({len(assistant_response)} chars)")
        return assistant_response

    except Exception as e:
        logger.error(f"Gemini API error in chat: {e}")
        raise


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting from Gemini response for clean speech output."""
    import re
    # Remove bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove italic: *text* or _text_
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    # Remove headers: ## text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Convert bullet asterisks to dashes
    text = re.sub(r'^\*\s+', '- ', text, flags=re.MULTILINE)
    # Remove backtick code formatting
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


# ─── GPA-Aware Advising ───────────────────────────────────────────

def build_gpa_guidance(gpa: Optional[float]) -> str:
    """Generate GPA-specific advising guidance to inject into the prompt."""
    if gpa is None or gpa == 0.0:
        return ""
    if gpa >= 3.5:
        return (
            f"\nStudent GPA: {gpa:.2f} (strong). "
            "They can handle a full 15-credit load including difficult courses. "
            "Feel free to recommend challenging upper-division courses together."
        )
    elif gpa >= 3.0:
        return (
            f"\nStudent GPA: {gpa:.2f} (above average). "
            "Limit to 1-2 notoriously difficult courses per semester (e.g. CS 3345, CS 4348, CS 4349). "
            "Pair hard courses with lighter electives."
        )
    elif gpa >= 2.5:
        return (
            f"\nStudent GPA: {gpa:.2f} (average). "
            "Do NOT put more than one of [CS 3345, CS 4348, CS 4349, CS 4384, MATH 2419] in the same semester. "
            "Prioritize grade recovery — recommend courses where the student is likely to earn an A. "
            "Consider suggesting 12 credit hours (4 courses) instead of 15 for tough semesters."
        )
    else:
        return (
            f"\nStudent GPA: {gpa:.2f} (needs improvement). "
            "IMPORTANT: Protect their GPA. Recommend only 12 credit hours per semester. "
            "Avoid all tier-3 difficulty courses until GPA improves above 2.5. "
            "Suggest courses known for high A-rates first. "
            "Explicitly mention the academic standing risk if they overload."
        )


# ─── Full 4-Year Plan Generation ─────────────────────────────────

class _PlannedCourse:
    def __init__(self, code: str, title: str, credits: int, reason: str):
        self.code = code
        self.title = title
        self.credits = credits
        self.reason = reason


class _SemesterPlan:
    def __init__(self, semester: str, courses: list, total_credits: int):
        self.semester = semester
        self.courses = courses
        self.total_credits = total_credits


def _validate_semester_credits(semester_name: str, courses: list, total_credits: int) -> tuple[list, int]:
    """Enforce credit hour limits: summer max 9, fall/spring max 18."""
    is_summer = "Summer" in semester_name
    max_hours = 9 if is_summer else 18
    while total_credits > max_hours and courses:
        removed = courses.pop()
        total_credits -= removed.get("credits", 3)
    return courses, total_credits


def _count_semesters_between(start: str, end: str) -> int:
    """Count the number of semesters between two semester labels (inclusive of end)."""
    import re as _re
    seasons = ["Spring", "Summer", "Fall"]

    def parse_sem(s: str) -> tuple:
        m = _re.match(r"(Spring|Summer|Fall)\s+(\d{4})", s, _re.IGNORECASE)
        if not m:
            return (0, 2026)  # fallback
        return (seasons.index(m.group(1).capitalize()), int(m.group(2)))

    start_idx, start_year = parse_sem(start)
    end_idx, end_year = parse_sem(end)

    # Calculate total semesters
    count = 0
    idx, year = start_idx, start_year
    while (year, idx) <= (end_year, end_idx):
        count += 1
        idx += 1
        if idx >= len(seasons):
            idx = 0
            year += 1
        if count > 20:  # safety limit
            break

    return max(1, count)


def _next_semesters(start: str, count: int) -> list[str]:
    """Generate a list of upcoming semester labels starting from `start`."""
    import re as _re
    seasons = ["Spring", "Summer", "Fall"]
    m = _re.match(r"(Spring|Summer|Fall)\s+(\d{4})", start, _re.IGNORECASE)
    if not m:
        # fallback
        return [f"Fall {2026 + i // 2}" for i in range(count)]
    season = m.group(1).capitalize()
    year = int(m.group(2))
    idx = seasons.index(season)
    result = []
    for _ in range(count):
        result.append(f"{seasons[idx]} {year}")
        idx += 1
        if idx >= len(seasons):
            idx = 0
            year += 1
    return result


async def generate_full_plan(
    transcript_context: str,
    career_goal: Optional[str],
    current_semester: str,
    total_credit_hours: float,
    gpa: Optional[float] = None,
    target_graduation: Optional[str] = None,
    start_semester: Optional[str] = None,
    major: Optional[str] = None,
    completed_courses: Optional[list[str]] = None,
) -> dict:
    """
    Generate a complete multi-semester academic plan using Gemini.

    Args:
        transcript_context: Full transcript summary
        career_goal: Optional career interest
        current_semester: Starting semester (e.g., "Fall 2026")
        total_credit_hours: Credits completed so far
        gpa: Student's cumulative GPA
        target_graduation: Optional target graduation (e.g., "Spring 2027" for early graduation)
        start_semester: When the student first enrolled (e.g., "Fall 2024")
        major: Student's major for degree plan lookup
        completed_courses: List of completed course codes

    Returns:
        dict with 'semesters' list and 'graduation_semester'
    """
    if not client:
        return {"semesters": [], "graduation_semester": "Unknown", "total_semesters": 0}

    import math
    from services.degree_plans import (
        get_degree_plan, get_remaining_courses, get_all_required_courses,
    )

    # Look up degree plan
    plan = get_degree_plan(major or "Computer Science")
    TOTAL_DEGREE_HOURS = plan.get("total_hours", 124)
    AVG_HOURS_PER_SEMESTER = 15
    MAX_FALL_SPRING_HOURS = 18
    MAX_SUMMER_HOURS = 9

    remaining_hours = max(0, TOTAL_DEGREE_HOURS - total_credit_hours)
    semesters_remaining = math.ceil(remaining_hours / AVG_HOURS_PER_SEMESTER)

    # Build remaining courses from degree plan
    completed_set = set(completed_courses or [])
    remaining_by_cat = get_remaining_courses(plan, list(completed_set))
    prereq_chains = plan.get("prerequisite_chains", {})

    remaining_courses_text = ""
    for cat_key, courses in remaining_by_cat.items():
        cat_label = plan["categories"].get(cat_key, {}).get("label", cat_key)
        remaining_courses_text += f"\n{cat_label}:\n"
        for code in courses:
            prereqs = prereq_chains.get(code, [])
            prereq_str = f" (prereqs: {', '.join(prereqs)})" if prereqs else ""
            remaining_courses_text += f"  - {code}{prereq_str}\n"

    all_prereqs_text = ""
    for course, prereqs in prereq_chains.items():
        if course not in completed_set and prereqs:
            all_prereqs_text += f"  {course} requires: {', '.join(prereqs)}\n"

    # Calculate expected graduation if start_semester provided
    if not target_graduation and start_semester:
        # 4 years from start = 8 fall/spring semesters
        import re as _re
        m = _re.match(r"(Spring|Summer|Fall)\s+(\d{4})", start_semester, _re.IGNORECASE)
        if m:
            start_year = int(m.group(2))
            grad_year = start_year + 4
            target_graduation = f"Spring {grad_year}"

    # Calculate minimum possible semesters (with max credits)
    min_possible_semesters = math.ceil(remaining_hours / MAX_FALL_SPRING_HOURS)

    # Early graduation handling
    early_grad_note = ""
    if target_graduation:
        # Count semesters from current to target
        target_sems = _count_semesters_between(current_semester, target_graduation)
        if target_sems < min_possible_semesters:
            early_grad_note = (
                f"\n\nEARLY GRADUATION REQUEST: Student requested {target_graduation}, "
                f"but this requires {remaining_hours} credits in {target_sems} semesters. "
                f"This is NOT POSSIBLE without exceeding UTD's max credit limits or violating prerequisite chains. "
                f"Generate the FASTEST realistic plan ({min_possible_semesters}+ semesters) and set the 'note' field to: "
                f"'Sorry, it is not possible to graduate by {target_graduation} without exceeding UTD's maximum allowed credits per semester or violating prerequisite chains. The fastest possible plan is shown below.'"
            )
        else:
            early_grad_note = (
                f"\n\nTARGET GRADUATION: {target_graduation}. "
                f"Generate a plan that reaches this goal. Adjust credit loads as needed "
                f"(up to 18/Fall-Spring, 9/Summer)."
            )
            semesters_remaining = target_sems

    gpa_note = build_gpa_guidance(gpa)

    semester_labels = _next_semesters(current_semester, max(semesters_remaining, min_possible_semesters) + 2)

    prompt = f"""You are CometAdvisor, an AI-powered academic advisor generating a COMPLETE multi-semester degree plan for a UTD student from NOW until GRADUATION.

STUDENT DATA (from parsed transcript):
{transcript_context}

Career goal: {career_goal or "General ECS degree"}
Starting semester: {current_semester}
{f"Student started college: {start_semester}" if start_semester else ""}
{f"Expected graduation: {target_graduation}" if target_graduation else ""}
Completed credit hours: {total_credit_hours}
Remaining hours to graduate ({TOTAL_DEGREE_HOURS} total required): {remaining_hours}
Estimated semesters remaining: {semesters_remaining}
{gpa_note}
{early_grad_note}

SEMESTERS TO PLAN (generate ALL of these): {", ".join(semester_labels[:semesters_remaining + 1])}

REMAINING REQUIRED COURSES (from official degree plan — you MUST schedule ALL of these):
{remaining_courses_text}

PREREQUISITE CHAINS (MUST ENFORCE — a course CANNOT appear before its prereqs):
{all_prereqs_text}

YOUR TASK:
Generate a COMPLETE semester-by-semester plan from {current_semester} until graduation. Each semester is a column in a horizontally scrollable board. Include EVERY remaining required course distributed across all semesters until graduation.

MULTI-DISCIPLINARY REQUIREMENTS (CRITICAL):
- A CS degree requires MORE than just CS courses. You MUST include:
  - Math: MATH 2413, MATH 2414, MATH 2418 (if not completed)
  - Physics: PHYS 2325, PHYS 2125, PHYS 2326, PHYS 2126 (if not completed)
  - Core curriculum: RHET 1302, GOVT 2305, GOVT 2306, ECS 2390
  - CS courses: All required core and electives
- Do NOT generate a plan with only CS courses — that is INVALID

CREDIT HOUR RULES (STRICT UTD POLICY):
- Fall/Spring semesters: 12-18 credit hours (target 15 = 5 courses × 3 credits)
- Summer semesters: MAXIMUM 9 credit hours (3 courses) — NO MORE
- NEVER exceed 6 courses (18 credits) in Fall/Spring or 3 courses (9 credits) in Summer
- If target graduation is impossible within these limits, explain why in the "note" field

PREREQUISITE CHAINS (MUST ENFORCE):
- MATH: MATH 2413 → MATH 2414 → MATH 2418
- Physics: MATH 2413 → PHYS 2325 (coreq: MATH 2414), PHYS 2325 → PHYS 2326
- CS early: CS 1436 → CS 1337 → CS 2336 → CS 3345
- CS core: CS 2305 + CS 2336 → CS 3345 → CS 4349
- CS systems: CS 2340 + CS 3377 + CS 3345 → CS 4348
- CS upper: CS 3345 → CS 4347, CS 4337, CS 4384
- CS capstone: CS 3354 + CS 3345 → CS 4485
- A course CANNOT appear in a semester unless ALL its prereqs are in earlier semesters or completed

COURSE OFFERING PATTERNS:
- Most CS courses: offered every Fall and Spring
- CS 4485 (Senior Project): typically Fall only or requires 2-semester sequence
- Summer: limited offerings — prefer core curriculum and math courses

OUTPUT FORMAT (ONLY valid JSON, no markdown fences, no explanation):
{{
  "semesters": [
    {{
      "semester": "Fall 2026",
      "courses": [
        {{"code": "CS 3345", "title": "Data Structures and Algorithms", "credits": 3, "reason": "Core requirement, prereqs met"}},
        {{"code": "MATH 2418", "title": "Linear Algebra", "credits": 4, "reason": "Math requirement, prereq for CS 3341"}},
        {{"code": "PHYS 2326", "title": "Electromagnetism", "credits": 3, "reason": "Physics requirement"}},
        {{"code": "GOVT 2305", "title": "Government I", "credits": 3, "reason": "Core curriculum"}},
        {{"code": "CS 3377", "title": "Systems Programming", "credits": 3, "reason": "Core requirement"}}
      ],
      "total_credits": 16
    }},
    {{
      "semester": "Spring 2027",
      "courses": [...],
      "total_credits": 15
    }}
  ],
  "graduation_semester": "Spring 2028",
  "note": "Plan includes all remaining degree requirements. Graduation in Spring 2028 with standard 15-credit semesters."
}}"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                system_instruction="You generate academic plans as JSON only. No markdown fences, no explanation.",
            ),
        )

        raw = (response.text or "").strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        raw = raw.strip()

        plan = json.loads(raw)

        # Validate and enforce credit limits per semester
        for sem in plan.get("semesters", []):
            sem["courses"], sem["total_credits"] = _validate_semester_credits(
                sem.get("semester", ""),
                sem.get("courses", []),
                sem.get("total_credits", 0),
            )

        plan["total_semesters"] = len(plan.get("semesters", []))
        return plan

    except Exception as e:
        logger.error(f"generate_full_plan failed: {e}")
        return {"semesters": [], "graduation_semester": "Unknown", "total_semesters": 0, "error": str(e)}



