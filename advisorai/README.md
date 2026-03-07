# AdvisorAI

Your intelligent academic advisor powered by AI.

## Project Structure

```
advisorai/
├── frontend/                 # Next.js frontend
│   ├── app/                  # App router pages
│   │   ├── page.tsx          # Home page
│   │   ├── dashboard/        # Student dashboard
│   │   ├── roadmap/          # Academic roadmap view
│   │   └── advisor/          # Voice advisor interface
│   ├── components/           # React components
│   │   ├── TranscriptUpload  # Upload transcripts
│   │   ├── CourseCard        # Course display card
│   │   ├── ScheduleGrid      # Schedule visualization
│   │   ├── RoadmapGraph      # Degree progress graph
│   │   └── VoiceAdvisor      # Voice interaction
│   └── lib/
│       └── api.ts            # API client
│
├── backend/                  # FastAPI backend
│   ├── main.py               # App entry point
│   ├── routers/
│   │   ├── recommend.py      # Recommendation endpoints (SUALS PART)
│   │   ├── courses.py        # Course data endpoints
│   │   └── voice.py          # Voice query endpoints
│   ├── services/
│   │   ├── nebula.py         # Nebula API client
│   │   ├── recommender.py    # Scoring & course selection (SUALS PART)
│   │   ├── llm.py            # Claude prompts & reasoning (SUALS PART)
│   │   └── transcript_parser.py
│   └── models/
│       └── schemas.py        # Pydantic models
│
└── README.md
```

## Getting Started

### Backend

```bash
cd backend
pip install fastapi uvicorn httpx pydantic pypdf
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend
- `ANTHROPIC_API_KEY` - Claude API key
- `NEBULA_API_URL` - Nebula API base URL
- `NEBULA_API_KEY` - Nebula API key

### Frontend
- `NEXT_PUBLIC_API_URL` - Backend API URL

## Team Responsibilities

- **SUALS PART**: `recommend.py`, `recommender.py`, `llm.py` - Recommendation engine and LLM integration
