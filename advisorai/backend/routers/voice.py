"""
Voice/Chat router — Gemini-powered conversation with transcript + course catalog context.

Endpoints:
  POST /api/voice/start — Start conversation with greeting
  POST /api/voice/chat  — Send message, get AI response (with real course data)
"""

import logging
import re
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services import llm
from services.data_loader import get_course_store

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_RELEVANT_COURSES = 8
MAX_DESCRIPTION_CHARS = 120
MAX_ENROLLMENT_REQ_CHARS = 100
MAX_CONTEXT_CHARS = 8000
MAX_COMPLETED_COURSES = 60


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    transcript_context: Optional[str] = None
    concise: bool = True  # Default ON for voice


class BoardAction(BaseModel):
    action: str          # "ADD", "REMOVE", "MOVE"
    course_code: str     # e.g. "CS 4375"
    semester: str        # e.g. "Fall 2027" (target for ADD, source for REMOVE)
    to_semester: Optional[str] = None  # Only for MOVE actions


class ChatResponse(BaseModel):
    reply: str
    history: list[ChatMessage]
    board_actions: list[BoardAction] = []
    suggest_regenerate: bool = False
    suggest_regenerate_reason: Optional[str] = None


ADVISOR_GREETING = (
    "Hey there! I'm Comet Advisor, your AI academic advisor at UTD. "
    "I've got your transcript pulled up and I'm ready to help you plan "
    "your courses. What would you like to know?"
)

# Common UTD subject prefixes to detect in messages
SUBJECT_PREFIXES = [
    "CS", "SE", "CE", "EE", "CGS", "COGS", "MATH", "STAT", "PHYS",
    "BMEN", "MECH", "ENGR", "BIOL", "CHEM", "ARTS", "HIST", "GOVT",
    "ECON", "PSY", "SOC", "COMM", "ATCM", "BA", "FIN", "MKT", "OPRE",
    "ACCT", "MIS", "OBHR", "IMS", "GEOS", "NATS", "RHET", "HUMA",
]


def _build_course_entry(code: str, store) -> str:
    """Build a detailed course entry string with prereqs and description."""
    info = store.get_course(code)
    if not info:
        return f"{code}: (not found in catalog)"
    
    parts = [f"{code}: {info.title} ({info.credits} credits)"]
    
    if info.description:
        # Truncate long descriptions
        desc = info.description[:MAX_DESCRIPTION_CHARS] + "..." if len(info.description) > MAX_DESCRIPTION_CHARS else info.description
        parts.append(f"  Description: {desc}")
    
    # Get prerequisites
    prereqs = store.get_prerequisites(code)
    if prereqs:
        parts.append(f"  Prerequisites: {', '.join(prereqs)}")
    elif info.enrollment_reqs:
        reqs = info.enrollment_reqs[:MAX_ENROLLMENT_REQ_CHARS] + "..." if len(info.enrollment_reqs) > MAX_ENROLLMENT_REQ_CHARS else info.enrollment_reqs
        parts.append(f"  Enrollment Requirements: {reqs}")
    else:
        parts.append(f"  Prerequisites: None")
    
    return "\n".join(parts)


def _extract_relevant_courses(message: str, history: list[ChatMessage]) -> str:
    """Search our course catalog for courses relevant to the user's message."""
    store = get_course_store()
    if not store.courses:
        return ""

    full_text = message.lower()
    recent_text = " ".join(msg.content.lower() for msg in history[-2:])

    explicit_codes: list[str] = []
    topic_codes: list[str] = []

    def add_unique(target: list[str], code: str):
        if code not in target and store.get_course(code):
            target.append(code)

    # Look for topic keywords in current message first, then very recent context.
    topic_keywords = {
        "machine learning": ["CS 4375", "CS 4395", "CS 6375", "CS 6363"],
        "artificial intelligence": ["CS 4365", "CS 6364"],
        "data science": ["CS 4352", "CS 4391", "STAT 4382"],
        "cybersecurity": ["CS 4389", "CS 4393", "CS 6324"],
        "software engineer": ["CS 3354", "SE 3354", "CS 4361", "SE 4351"],
        "operating system": ["CS 4348", "CS 6378"],
        "algorithm": ["CS 3345", "CS 4349"],
        "database": ["CS 4347", "CS 6360"],
        "cognitive science": ["CGS 2301", "CGS 3325", "CGS 3342", "CGS 3361"],
        "network": ["CS 4390", "CS 6390"],
        "computer vision": ["CS 4391", "CS 6366"],
        "web development": ["CS 4337"],
        "graphics": ["CS 4361", "CS 6366"],
        "compiler": ["CS 4386"],
        "deep learning": ["CS 4395", "CS 6375"],
        "natural language": ["CS 4395"],
        "robotics": ["CS 4365", "SE 4367"],
        "game": ["CS 4361", "CS 4361"],
    }

    for keyword, codes in topic_keywords.items():
        if keyword in full_text or keyword in recent_text:
            for code in codes:
                add_unique(topic_codes, code)

    # Look for specific course code mentions (e.g., "CS 1337", "CGS 2301").
    code_pattern = re.compile(r'\b([A-Z]{2,4})\s*(\d{4})\b')
    for match in code_pattern.finditer(f"{message} {recent_text}".upper()):
        code = f"{match.group(1)} {match.group(2)}"
        add_unique(explicit_codes, code)

    # Avoid dumping whole subject catalogs into prompt. Bare prefix mentions are too expensive.
    # Keep only explicitly mentioned and topic-relevant courses.
    ordered_codes: list[str] = []
    for code in explicit_codes + topic_codes:
        if code not in ordered_codes:
            ordered_codes.append(code)

    if not ordered_codes:
        return ""

    entries = [_build_course_entry(code, store) for code in ordered_codes[:MAX_RELEVANT_COURSES]]

    return "RELEVANT UTD COURSES FROM OFFICIAL CATALOG (this is authoritative data):\n\n" + "\n\n".join(entries)


def _compact_context(full_context: str) -> str:
    """Trim oversized context so Gemini sees only the most useful parts."""
    if not full_context:
        return full_context

    lines = full_context.splitlines()
    compacted: list[str] = []

    for line in lines:
        if line.startswith("Completed Courses:"):
            course_blob = line.split(":", 1)[1].strip() if ":" in line else ""
            courses = [c.strip() for c in course_blob.split(";") if c.strip()]
            if len(courses) > MAX_COMPLETED_COURSES:
                kept = courses[-MAX_COMPLETED_COURSES:]
                compacted.append(
                    f"Completed Courses ({len(kept)} most recent of {len(courses)}): " + "; ".join(kept)
                )
            else:
                compacted.append(line)
        else:
            compacted.append(line)

    compact = "\n".join(compacted).strip()
    if len(compact) <= MAX_CONTEXT_CHARS:
        return compact

    head = int(MAX_CONTEXT_CHARS * 0.7)
    tail = MAX_CONTEXT_CHARS - head - len("\n...[truncated for speed]...\n")
    return compact[:head].rstrip() + "\n...[truncated for speed]...\n" + compact[-tail:].lstrip()


@router.post("/start", response_model=ChatResponse)
async def start_conversation() -> ChatResponse:
    """Start a new conversation with a greeting."""
    greeting_message = ChatMessage(role="model", content=ADVISOR_GREETING)
    return ChatResponse(
        reply=ADVISOR_GREETING,
        history=[greeting_message],
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message and get the advisor's response via Gemini."""
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history
    ]

    # Search our course catalog for relevant courses
    course_context = _extract_relevant_courses(request.message, request.history)

    # Combine transcript + course catalog context
    full_context = request.transcript_context or ""
    if course_context:
        full_context += ("\n\n" if full_context else "") + course_context
    full_context = _compact_context(full_context)

    try:
        advisor_reply = await llm.chat_with_advisor(
            conversation_history=conversation_history,
            user_message=request.message,
            transcript_context=full_context if full_context else None,
            concise=request.concise,
        )
    except Exception as e:
        logger.error(f"LLM chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get response from advisor: {str(e)}",
        )

    # Parse board actions from AI response
    board_actions = []
    clean_reply = advisor_reply
    action_pattern = re.compile(r'\[ACTION:(ADD|REMOVE|MOVE)\|([^\]]+)\]')
    action_matches = action_pattern.findall(advisor_reply)

    for action_type, params in action_matches:
        parts = [p.strip() for p in params.split('|')]
        if action_type == 'ADD' and len(parts) >= 2:
            board_actions.append(BoardAction(action='ADD', course_code=parts[0], semester=parts[1]))
        elif action_type == 'REMOVE' and len(parts) >= 2:
            board_actions.append(BoardAction(action='REMOVE', course_code=parts[0], semester=parts[1]))
        elif action_type == 'MOVE' and len(parts) >= 3:
            board_actions.append(BoardAction(action='MOVE', course_code=parts[0], semester=parts[1], to_semester=parts[2]))

    # Parse SUGGEST_REGENERATE action
    suggest_regenerate = False
    suggest_regenerate_reason = None
    regen_pattern = re.compile(r'\[ACTION:SUGGEST_REGENERATE\|([^\]]*)\]')
    regen_match = regen_pattern.search(advisor_reply)
    if regen_match:
        suggest_regenerate = True
        suggest_regenerate_reason = regen_match.group(1).strip() or "Your goals have changed"

    # Strip action tags from spoken reply
    clean_reply = re.sub(r'\[ACTION:[^\]]*\]', '', advisor_reply).strip()
    # Clean up leftover blank lines
    clean_reply = re.sub(r'\n{2,}', '\n', clean_reply).strip()

    # Build updated history (store clean reply without action tags)
    updated_history = list(request.history)
    updated_history.append(ChatMessage(role="user", content=request.message))
    updated_history.append(ChatMessage(role="model", content=clean_reply))

    return ChatResponse(
        reply=clean_reply,
        history=updated_history,
        board_actions=board_actions,
        suggest_regenerate=suggest_regenerate,
        suggest_regenerate_reason=suggest_regenerate_reason,
    )
