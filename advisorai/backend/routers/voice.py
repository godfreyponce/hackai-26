"""
Voice/Chat router for AdvisorAI.
Handles text-based conversation with the AI academic advisor.

Endpoints:
  POST /api/voice/start - Start a new conversation with greeting
  POST /api/voice/chat  - Continue conversation with user message
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services import llm

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: Literal["user", "model"]
    content: str


class ChatRequest(BaseModel):
    """Request body for /chat endpoint."""
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    """Response body for /chat and /start endpoints."""
    reply: str
    history: list[ChatMessage]


# ============================================================================
# Endpoints
# ============================================================================

ADVISOR_GREETING = (
    "Hey there! I'm your UTD academic advisor assistant. "
    "I'm here to help you plan your courses, explore degree requirements, "
    "and figure out what classes might be a good fit for you. "
    "What are you looking for this semester?"
)


@router.post(
    "/start",
    response_model=ChatResponse,
    summary="Start a new conversation",
    description="Begins a fresh conversation with a greeting from the advisor.",
)
async def start_conversation() -> ChatResponse:
    """
    Start a new conversation with a hardcoded greeting.
    Does not call the LLM - just returns a friendly opening message.
    """
    greeting_message = ChatMessage(role="model", content=ADVISOR_GREETING)

    return ChatResponse(
        reply=ADVISOR_GREETING,
        history=[greeting_message],
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the advisor",
    description="Continues the conversation by sending a user message and receiving an advisor reply.",
    responses={
        200: {"description": "Successful response with advisor reply"},
        500: {"description": "LLM call failed"},
    },
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user message and return the advisor's response.

    The client maintains conversation state by sending the full history
    with each request. The server returns the updated history including
    the new exchange.
    """
    # Convert history to the format expected by llm.chat_with_advisor
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history
    ]

    try:
        # Call the LLM service
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

    # Build updated history with the new exchange
    updated_history = list(request.history)
    updated_history.append(ChatMessage(role="user", content=request.message))
    updated_history.append(ChatMessage(role="model", content=advisor_reply))

    return ChatResponse(
        reply=advisor_reply,
        history=updated_history,
    )
