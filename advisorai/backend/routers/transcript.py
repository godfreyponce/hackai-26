"""
Transcript upload router — POST /api/transcript

Accepts a PDF file upload, runs it through the transcript parser,
and returns the structured TranscriptData JSON.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException

from models.schemas import TranscriptData
from services.transcript_parser import TranscriptParser

router = APIRouter()
parser = TranscriptParser()


@router.post("/", response_model=TranscriptData)
async def upload_transcript(file: UploadFile = File(...)):
    """
    Upload a UTD unofficial transcript PDF and get structured data back.

    Returns student name, major, GPA, total credit hours,
    and all completed courses with grades and semester tags.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported. Please upload your unofficial transcript PDF.",
        )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        result = parser.parse(content, file.filename)
        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse transcript: {str(e)}",
        )
