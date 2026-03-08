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
        desc = info.description[:200] + "..." if len(info.description) > 200 else info.description
        parts.append(f"  Description: {desc}")
    
    # Get prerequisites
    prereqs = store.get_prerequisites(code)
    if prereqs:
        parts.append(f"  Prerequisites: {', '.join(prereqs)}")
    elif info.enrollment_reqs:
        reqs = info.enrollment_reqs[:150] + "..." if len(info.enrollment_reqs) > 150 else info.enrollment_reqs
        parts.append(f"  Enrollment Requirements: {reqs}")
    else:
        parts.append(f"  Prerequisites: None")
    
    return "\n".join(parts)


def _extract_relevant_courses(message: str, history: list[ChatMessage]) -> str:
    """Search our course catalog for courses relevant to the user's message."""
    store = get_course_store()
    if not store.courses:
        return ""

    # Combine message + recent history for context
    full_text = message.lower()
    for msg in history[-4:]:  # Last 4 messages
        full_text += " " + msg.content.lower()

    found_codes = set()

    # 1. Look for explicit subject prefixes mentioned as standalone words
    for prefix in SUBJECT_PREFIXES:
        pattern = r'\b' + re.escape(prefix) + r'\b'
        if re.search(pattern, message, re.IGNORECASE):
            for code in store.courses:
                if code.startswith(prefix + " "):
                    found_codes.add(code)

    # 2. Look for topic keywords
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
        if keyword in full_text:
            found_codes.update(codes)

    # 3. Look for specific course code mentions (e.g., "CS 1337", "CGS 2301")
    code_pattern = re.compile(r'\b([A-Z]{2,4})\s*(\d{4})\b')
    for match in code_pattern.finditer(message.upper()):
        code = f"{match.group(1)} {match.group(2)}"
        if store.get_course(code):
            found_codes.add(code)

    if not found_codes:
        return ""

    # Sort and limit to 25 courses, build detailed entries
    sorted_codes = sorted(found_codes)[:25]
    entries = [_build_course_entry(code, store) for code in sorted_codes]

    return "RELEVANT UTD COURSES FROM OFFICIAL CATALOG (this is authoritative data):\n\n" + "\n\n".join(entries)


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
    )
