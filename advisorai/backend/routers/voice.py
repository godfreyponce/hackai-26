from fastapi import APIRouter, UploadFile, File
from typing import Optional

from services.llm import process_voice_query

router = APIRouter()


@router.post("/query")
async def voice_query(audio: UploadFile = File(...)):
    """Process a voice query and return advisor response."""
    audio_bytes = await audio.read()

    # TODO: Transcribe audio using speech-to-text
    transcription = ""  # Placeholder

    # Process with LLM
    response = await process_voice_query(transcription)

    return {
        "transcription": transcription,
        "response": response,
    }


@router.post("/synthesize")
async def synthesize_speech(text: str):
    """Convert text response to speech."""
    # TODO: Implement text-to-speech
    return {"audio_url": None, "text": text}
