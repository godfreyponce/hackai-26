from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import recommend, courses, voice

app = FastAPI(title="AdvisorAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend.router, prefix="/api/recommend", tags=["recommend"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])


@app.get("/")
async def root():
    return {"message": "AdvisorAI API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
