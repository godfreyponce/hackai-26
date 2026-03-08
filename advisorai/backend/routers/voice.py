"""
Voice/Chat router — Gemini-powered conversation.

Endpoints:
  POST /api/voice/start — Start conversation with greeting
  POST /api/voice/chat  — Send message, get AI response
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services import llm

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    history: list[ChatMessage]


ADVISOR_GREETING = (
    "Hey there! I'm Comet Advisor, your AI academic advisor at UTD. "
    "I'm here to help you plan your courses, explore degree requirements, "
    "and figure out what classes might be a good fit for you. "
    "What are you looking for this semester?"
)


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

    try:
        advisor_reply = await llm.chat_with_advisor(
            conversation_history=conversation_history,
            user_message=request.message,
        )
    except Exception as e:
        logger.error(f"LLM chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get response from advisor: {str(e)}",
        )

    # Build updated history
    updated_history = list(request.history)
    updated_history.append(ChatMessage(role="user", content=request.message))
    updated_history.append(ChatMessage(role="model", content=advisor_reply))

    return ChatResponse(
        reply=advisor_reply,
        history=updated_history,
    )
