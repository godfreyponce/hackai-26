# AdvisorAI

AdvisorAI is an intelligent academic planning assistant for UTD students. It provides personalized course recommendations and semester schedules by integrating hardcoded UTD degree flowcharts, unofficial transcript uploads, and real-time course data from Nebula Labs APIs. The system uses Claude (Anthropic API) for natural-language explanations and ElevenLabs TTS with Web Speech API for voice interaction.

The backend recommendation engine scores courses based on student interests, professor quality, and availability, then generates friendly explanations for each recommendation. Students can upload their transcripts, specify career interests, and receive tailored course schedules that fit their goals and constraints.

## Tech Stack

- **Frontend:** Next.js (React) + TailwindCSS
- **Backend:** FastAPI (Python)
- **Voice:** ElevenLabs TTS + Web Speech API
- **Data:** Hardcoded UTD flowcharts + Nebula Labs APIs
- **Visualization:** React Flow / D3.js
- **Deployment:** Vercel (frontend) + Railway/Render (backend)

## Running the Backend Locally

```bash
cd advisorai/backend
pip install -r ../requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## Environment Variables

Create a `.env` file in the `backend/` directory:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
NEBULA_API_KEY=your_nebula_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

## Project Structure

```
advisorai/
├── frontend/                           # Next.js frontend (TEAMMATE SCOPE)
│   ├── app/
│   │   ├── page.tsx                    # Home page
│   │   ├── dashboard/page.tsx          # Student dashboard
│   │   ├── roadmap/page.tsx            # Degree roadmap visualization
│   │   └── advisor/page.tsx            # Voice advisor interface
│   ├── components/
│   │   ├── TranscriptUpload.tsx        # Transcript upload component
│   │   ├── CourseCard.tsx              # Course display card
│   │   ├── ScheduleGrid.tsx            # Schedule visualization
│   │   ├── RoadmapGraph.tsx            # Degree progress graph
│   │   └── VoiceAdvisor.tsx            # Voice interaction UI
│   └── lib/
│       └── api.ts                      # API client
│
├── backend/
│   ├── main.py                         # FastAPI app entry (TEAMMATE SCOPE)
│   ├── routers/
│   │   ├── recommend.py                # ✅ SUAL'S SCOPE - Recommendation endpoint
│   │   ├── courses.py                  # Course data endpoints (TEAMMATE SCOPE)
│   │   └── voice.py                    # Voice endpoints (TEAMMATE SCOPE)
│   ├── services/
│   │   ├── nebula.py                   # Nebula API client (TEAMMATE SCOPE)
│   │   ├── recommender.py              # ✅ SUAL'S SCOPE - Scoring engine
│   │   ├── llm.py                      # ✅ SUAL'S SCOPE - Claude integration
│   │   └── transcript_parser.py        # Transcript parsing (TEAMMATE SCOPE)
│   └── models/
│       └── schemas.py                  # ✅ SUAL'S SCOPE - Pydantic schemas
│
├── .gitignore
├── requirements.txt
└── README.md
```

## Sual's Scope (Recommendation Engine)

### Files Implemented

1. **`backend/models/schemas.py`** - Pydantic models for all data structures
2. **`backend/services/recommender.py`** - Course scoring and filtering logic
3. **`backend/services/llm.py`** - Claude API integration for reasoning
4. **`backend/routers/recommend.py`** - POST /api/recommend endpoint

### API Endpoint

**POST /api/recommend**

Request body:
```json
{
  "completed_courses": [
    {"course_id": "CS 1337", "course_name": "Computer Science I", "grade": "A", "credits": 3}
  ],
  "student_interest": "machine learning",
  "credit_limit": 15,
  "scheduling_preference": "morning classes",
  "major": "Computer Science"
}
```

Response:
```json
{
  "recommended_courses": [
    {
      "course_id": "CS 4375",
      "course_name": "Introduction to Machine Learning",
      "credits": 3,
      "score": 0.85,
      "label": "career-aligned",
      "professor": {
        "professor_id": "prof123",
        "professor_name": "Dr. Smith",
        "avg_grade": 3.5,
        "consistency_score": 0.8
      },
      "reasoning": "This course directly aligns with your machine learning interest..."
    }
  ],
  "alternative_career_paths": [
    {
      "career": "Data Scientist",
      "reasoning": "Your coursework in statistics and programming provides a strong foundation..."
    }
  ]
}
```

### Scoring Formula

```
score = 0.5 * student_priority + 0.3 * professor_rating + 0.2 * availability_score
```

- **student_priority**: 1.0 (exact interest match), 0.5 (partial match), 0.0 (no match)
- **professor_rating**: Combined score from avg_grade and grade_consistency
- **availability_score**: Based on number of open sections

## Teammate Scope (Stubs)

The following files are stubs awaiting implementation:

- `backend/main.py` - FastAPI app initialization and router mounting
- `backend/routers/courses.py` - Course lookup endpoints
- `backend/routers/voice.py` - Voice interaction endpoints
- `backend/services/nebula.py` - Nebula Labs API client
- `backend/services/transcript_parser.py` - Transcript parsing and degree requirements
- All `frontend/` files

## License

MIT
