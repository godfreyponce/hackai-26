"""
main.py — AdvisorAI FastAPI Backend

Routes:
  POST /api/transcript     — Upload transcript PDF, get parsed JSON
  POST /api/recommend      — Upload transcript + career goal, get semester plan
  GET  /api/recommend/{id} — Get recommendations by student ID
  GET  /api/courses        — Search course catalog
  POST /api/voice/query    — Voice query (teammate's part)
"""

# Load .env first, before any other imports that might need env vars
from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import recommend, courses, voice, transcript
from services.data_loader import get_course_store, fetch_and_cache_courses_async

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load course data on startup."""
    logger.info("Loading UTD course data...")
    # Fetch courses from Nebula API if cache is stale (async-safe)
    await fetch_and_cache_courses_async()
    store = get_course_store()
    logger.info(f"Ready — {len(store.courses)} courses loaded")
    yield


app = FastAPI(
    title="AdvisorAI API",
    description="Intelligent academic planning assistant for UTD students",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(transcript.router, prefix="/api/transcript", tags=["transcript"])
app.include_router(recommend.router, prefix="/api/recommend", tags=["recommend"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])


@app.get("/")
async def root():
    return {
        "message": "AdvisorAI API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/transcript — Upload transcript PDF",
            "POST /api/recommend — Get semester plan",
            "GET /api/courses — Search courses",
            "POST /api/voice/query — Voice query",
        ],
    }


@app.get("/health")
async def health():
    store = get_course_store()
    return {
        "status": "healthy",
        "courses_loaded": len(store.courses),
        "degrees_loaded": len(store.degrees),
    }
