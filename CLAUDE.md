# CometAdvisor — Claude Code Engineering Prompt

## Project Overview

CometAdvisor is an AI-powered academic advisor for UTD students. It has:
- **Frontend**: Next.js 14 app (`app/`, `components/`) running on port 3000
- **Backend**: FastAPI Python server (`advisorai/backend/`) running on port 8000
- **Voice**: ElevenLabs TTS via `/api/speak` Next.js route, Web Speech API for mic input
- **AI**: Google Gemini (`gemini-2.5-flash`) for advisor conversation via `services/llm.py`
- **Data**: Nebula Labs API (`NEBULA_API_KEY`) for UTD course/professor/grade data

The student uploads a transcript PDF → it gets parsed → they enter a voice session with the AI advisor → the advisor helps plan their remaining degree courses on a drag-and-drop board.

---

## Nebula Labs API Reference

**Base URL**: `https://api.utdnebula.com`
**Auth**: `x-api-key: {NEBULA_API_KEY}` header on every request
**All responses**: `{ status: int, message: string, data: T }`
**Rate limit**: 1000 requests/minute/project

### Courses

#### `GET /course`
Search courses by field. All params are optional query strings.
```
subject_prefix  — e.g. "CS", "MATH", "SE"
course_number   — e.g. "3345"
title           — partial match on course title
credit_hours    — e.g. "3"
offset          — pagination (0-indexed)
```
Returns: `data: Course[]`

#### `GET /course/all`
Returns ALL courses (no params). Use for startup cache only — large payload.
Returns: `data: Course[]`

#### `GET /course/{id}`
Returns a single course by its MongoDB `_id`.
Returns: `data: Course`

#### `GET /course/{id}/grades`
Returns overall grade distribution array for a course.
Returns: `data: int[]` (28 integers — see grade index table below)

#### `GET /course/{id}/professors`
All professors who have ever taught this course.
Returns: `data: Professor[]`

#### `GET /course/{id}/sections`
All sections ever offered for this course.
Returns: `data: Section[]`

#### `GET /course/sections/trends`
**High-speed endpoint.** Sections with embedded Course + Professor data in one call. Required:
```
subject_prefix  — required, e.g. "CS"
course_number   — required, e.g. "3345"
```
Returns: `data: Section[]` (each section has `professor_details` and `course_details` embedded)
**Use this as the primary endpoint for professor/grade lookups — fewest round trips.**

### Professors

#### `GET /professor`
Search professors. All params optional:
```
first_name, last_name, titles, email, phone_number
offset
```
Returns: `data: Professor[]`

#### `GET /professor/all`
All professors. Large payload — use for startup cache only.
Returns: `data: Professor[]`

#### `GET /professor/{id}`
Single professor by MongoDB `_id`.
Returns: `data: Professor`

#### `GET /professor/{id}/grades`
Overall grade distribution aggregated across all sections taught by this professor.
Returns: `data: int[]` (28-integer array)

#### `GET /professor/{id}/courses`
All courses this professor has taught.
Returns: `data: Course[]`

#### `GET /professor/{id}/sections`
All sections taught by this professor.
Returns: `data: Section[]`

#### `GET /professor/sections/trends`
**High-speed endpoint.** Professor's sections with embedded course + grade data. Required:
```
first_name — required
last_name  — required
```
Returns: `data: Section[]`

### Grades

#### `GET /grades/overall`
Aggregate grade distribution filtered by any combination of params. All params optional:
```
prefix         — subject prefix, e.g. "CS"
number         — course number, e.g. "3345"
first_name     — professor first name
last_name      — professor last name
section_number — specific section number
```
Returns: `data: int[]` — 28-element grade distribution array

#### `GET /grades/semester`
Grade distributions broken down by semester.
Same params as `/grades/overall`.
Returns: `data: GradeData[]` where `GradeData = { _id: string, grade_distribution: int[] }`
(`_id` is the semester name, e.g. `"22F"`, `"23S"`)

#### `GET /grades/semester/sectionType`
Grade distributions broken down by section type per semester.
Same params as above.
Returns: `data: GradeData[]`

### Sections

#### `GET /section`
Search sections by instruction mode, core flags, academic session, etc.
Returns: `data: Section[]`

#### `GET /section/{id}`
Single section by `_id`.
Returns: `data: Section`

#### `GET /section/{id}/grades`
Grade distribution for a single section.
Returns: `data: int[]` (28-integer array)

#### `GET /section/{id}/professors`
Professors who taught a specific section.
Returns: `data: Professor[]`

### Key Schema Shapes

```typescript
Course = {
  _id: string
  subject_prefix: string        // "CS"
  course_number: string         // "3345"
  title: string                 // "Data Structures and Introduction to Algorithmic Analysis"
  description: string
  credit_hours: string          // "3"
  class_level: string
  activity_type: string
  prerequisites: CollectionRequirement   // nested: { name, options[], required, type }
  corequisites: CollectionRequirement
  co_or_pre_requisites: CollectionRequirement
  enrollment_reqs: string
  sections: string[]            // section _id references
  school: string
  offering_frequency: string
}

Professor = {
  _id: string
  first_name: string
  last_name: string
  titles: string[]
  email: string
  image_uri: string
  profile_uri: string
  sections: string[]            // section _id references
  phone_number: string
}

Section = {
  _id: string
  section_number: string
  academic_session: { name: string, start_date: string, end_date: string }
  professors: string[]          // professor _id references
  grade_distribution: int[]     // 28 integers (see table below)
  instruction_mode: string      // "face to face", "online", etc.
  meetings: Meeting[]
  core_flags: string[]
  course_reference: string      // course _id
  teaching_assistants: string[]
  syllabus_uri: string
  // When returned from /trends endpoints:
  professor_details?: Professor[]
  course_details?: Course
}

GradeData = {
  _id: string                   // semester identifier e.g. "22F"
  grade_distribution: int[]     // 28 integers
}

CollectionRequirement = {
  name: string
  options: (CourseRequirement | CollectionRequirement)[]
  required: int
  type: "collection"
}

CourseRequirement = {
  class_reference: string       // course _id
  minimum_grade: string
  type: "course"
}
```

### Grade Distribution Index Mapping (28 elements)
```
Index:  0    1    2    3    4    5    6    7    8    9   10   11   12   13
Grade: A+   A    A-   B+   B    B-   C+   C    C-   D+   D    D-   F   CR
Index: 14   15   16   17   18   19   20   21   22   23   24   25   26   27
Grade: NC   P    NP   I    W    NF   NR   null null TOT  null null null null

// A-rate formula:
a_rate = (dist[0] + dist[1] + dist[2]) / dist[23] * 100
// Only count professors where dist[23] >= 30 (meaningful sample size)
```

---

## Issues to Fix (in priority order)

### 1. Advisor Audio Self-Interrupts Once Per Response

**Bug**: Every time the advisor speaks, the audio cuts out and restarts once mid-response.

**Root Cause** (`app/session/page.tsx`):
- `handleSend()` sets `setAdvisorStatus("speaking")` and `setIsSpeaking(true)` before calling `playAudio()`
- React re-renders caused by those state updates may cause `<AIAvatar>` to re-mount or trigger a second `playAudio` invocation
- `audioRef.current.pause()` is called every time `playAudio` runs, cutting an already-playing response

**Fix**:
```typescript
const isPlayingRef = useRef(false);

const playAudio = async (text: string, onEnded?: () => void) => {
  if (isPlayingRef.current) return; // Guard: don't interrupt ongoing playback
  isPlayingRef.current = true;

  try {
    const res = await fetch("/api/speak", { ... });
    if (!res.ok) throw new Error("TTS failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }

    const audio = new Audio(url);
    audioRef.current = audio;
    setAdvisorStatus("speaking");
    setIsSpeaking(true);

    audio.onended = () => {
      isPlayingRef.current = false;
      setIsSpeaking(false);
      setAdvisorStatus("listening");
      if (onEnded) onEnded();
    };

    await audio.play();
  } catch {
    isPlayingRef.current = false;
    setIsSpeaking(false);
    setAdvisorStatus("listening");
    if (onEnded) onEnded();
  }
};
```
- Do NOT call `setAdvisorStatus("speaking")` or `setIsSpeaking(true)` in `handleSend()` before `playAudio` — let `playAudio` own those state transitions entirely.
- Debounce the speech recognition `handleSend` trigger with a 300ms debounce to prevent double-fire.

---

### 2. Full 4-Year Degree Completion Plan (not just next semester)

**Current behavior**: The DND board has only 3 static columns: `inProgress`, `recommended`, `later`.

**Desired behavior**: Generate a complete multi-semester plan covering ALL remaining semesters with one dynamic column per semester.

#### Calculation Logic
```python
TOTAL_DEGREE_HOURS = 124  # Standard UTD CS degree
AVG_HOURS_PER_SEMESTER = 15
remaining_hours = TOTAL_DEGREE_HOURS - transcript.total_credit_hours
semesters_remaining = ceil(remaining_hours / AVG_HOURS_PER_SEMESTER)
```

#### New Backend Endpoint: `POST /api/recommend/full-plan`

**File**: `advisorai/backend/routers/recommend.py`

```python
class FullPlanRequest(BaseModel):
    transcript_context: str
    career_goal: Optional[str] = None
    current_semester: str       # e.g. "Spring 2026"
    total_credit_hours: float

class PlannedCourse(BaseModel):
    code: str                   # e.g. "CS 3345"
    title: str
    credits: int
    reason: str

class SemesterPlan(BaseModel):
    semester: str               # e.g. "Fall 2026"
    courses: list[PlannedCourse]
    total_credits: int

class FullPlanResponse(BaseModel):
    semesters: list[SemesterPlan]
    total_semesters: int
    graduation_semester: str
```

**LLM Prompt** (new function `generate_full_plan()` in `services/llm.py`):
```
You are generating a complete multi-semester academic plan for a UTD CS student.

Student data:
{transcript_context}

Career goal: {career_goal}
Starting semester: {current_semester}
Completed credit hours: {total_credit_hours}
Remaining hours to graduate: {remaining_hours}
Estimated semesters remaining: {semesters_remaining}

STRICT RULES:
- Each Fall/Spring semester: exactly 15 credit hours (5 × 3-credit courses)
- Each Summer semester: 9 credit hours maximum (3 courses)
- Respect ALL prerequisites — a course cannot appear before its prereqs are completed
- Do not repeat any course already in the transcript
- Distribute lower-level courses in earlier semesters

Output ONLY valid JSON in this exact format, no other text:
{
  "semesters": [
    {
      "semester": "Fall 2026",
      "courses": [
        {"code": "CS 3345", "title": "Data Structures", "credits": 3, "reason": "Core requirement, prereqs met"},
        ...
      ],
      "total_credits": 15
    }
  ],
  "graduation_semester": "Spring 2028"
}
```

Parse with: strip markdown fences → `json.loads()` → validate with `FullPlanResponse` model → run credit hour validation.

#### Frontend Changes (`app/session/page.tsx`)

Add a **"Generate My Plan"** button that appears after 3+ chat exchanges. On click:
```typescript
const buildColumnsFromPlan = (plan: FullPlanResponse) => {
  const newColumns: Record<string, any> = {
    inProgress: columns.inProgress,  // preserve in-progress
  };

  plan.semesters.forEach((sem) => {
    const key = sem.semester.replace(/\s+/g, "_");
    newColumns[key] = {
      title: sem.semester,
      credits: sem.total_credits,
      courses: sem.courses.map(c => ({
        id: `${c.code}-${Math.random().toString(36).substr(2, 9)}`,
        code: c.code,
        title: c.title,
        professor: "Loading...",
        badge: "Core Requirement",
        whyText: c.reason,
      })),
    };
  });

  setColumns(newColumns);

  // Background-fetch professor recommendations for every course
  plan.semesters.flatMap(s => s.courses).forEach(c => fetchProfessorForCourse(c.code));
};
```

---

### 3. Credit Hour Limits Per Semester

**Rules**:
- Fall/Spring: 12 min, 18 max, 15 target
- Summer: 9–12 max
- Never suggest 19+ hours (requires academic petition)

#### Backend (`services/llm.py` — `CHAT_SYSTEM_PROMPT` addition):
```
CREDIT HOUR RULES — STRICTLY ENFORCE:
- Fall/Spring semesters: 12–18 credit hours (target: 15 = 5 courses × 3 credits)
- Summer semesters: maximum 9–12 credit hours (3–4 courses)
- NEVER suggest more than 6 courses in any single semester
- If a student asks for more, warn them it requires an academic petition
```

#### Backend validation in `generate_full_plan()`:
```python
def validate_semester_credits(sem: SemesterPlan) -> SemesterPlan:
    is_summer = "Summer" in sem.semester
    max_hours = 9 if is_summer else 18
    while sem.total_credits > max_hours and sem.courses:
        removed = sem.courses.pop()
        sem.total_credits -= removed.credits
    return sem
```

#### Frontend (`components/dnd-board.tsx`) — column header badge:
```typescript
const getCreditWarning = (credits: number, semester: string) => {
  const isSummer = semester.toLowerCase().includes("summer");
  const max = isSummer ? 9 : 18;
  if (credits > max) return "text-red-400";
  if (credits > 15 && !isSummer) return "text-yellow-400";
  if (credits < 12 && credits > 0) return "text-yellow-400";
  return "text-green-400";
};
// Render: <span className={getCreditWarning(...)}>{credits} hrs</span>
```

---

### 4. Professor Recommendations via Nebula Labs

**Current behavior**: All course cards show `professor: "TBD"`.

#### New Service: `advisorai/backend/services/nebula.py`

```python
import os, httpx
from typing import Optional

NEBULA_BASE = "https://api.utdnebula.com"
HEADERS = {"x-api-key": os.getenv("NEBULA_API_KEY", "")}

# Grade dist indices
A_INDICES = [0, 1, 2]   # A+, A, A-
TOTAL_INDEX = 23

async def get_best_professor(subject: str, course_number: str) -> Optional[dict]:
    """
    Calls GET /course/sections/trends to get all sections with embedded professor data.
    Aggregates A-rate per professor across all sections.
    Returns the professor with highest A-rate (minimum 30 total students).
    Returns: {"name": str, "a_rate": float, "total_students": int} or None
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{NEBULA_BASE}/course/sections/trends",
            params={"subject_prefix": subject, "course_number": course_number},
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None

        sections = resp.json().get("data", [])
        prof_stats: dict[str, dict] = {}

        for section in sections:
            dist = section.get("grade_distribution", [])
            if len(dist) < 24 or dist[TOTAL_INDEX] < 5:
                continue
            total = dist[TOTAL_INDEX]
            a_grades = sum(dist[i] for i in A_INDICES if i < len(dist))

            for prof in section.get("professor_details", []):
                name = f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip()
                if not name:
                    continue
                if name not in prof_stats:
                    prof_stats[name] = {"a_grades": 0, "total": 0}
                prof_stats[name]["a_grades"] += a_grades
                prof_stats[name]["total"] += total

        best = None
        best_rate = -1.0
        for name, stats in prof_stats.items():
            if stats["total"] < 30:
                continue
            rate = stats["a_grades"] / stats["total"]
            if rate > best_rate:
                best_rate = rate
                best = {"name": name, "a_rate": round(rate * 100, 1), "total_students": stats["total"]}

        return best
```

#### New Endpoint: `GET /api/courses/{course_code}/professor`

**File**: `advisorai/backend/routers/courses.py`:
```python
@router.get("/{course_code}/professor")
async def get_professor_for_course(course_code: str):
    """course_code: "CS 3345" or "CS3345" """
    parts = course_code.replace("-", " ").strip().split()
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid course code format. Use 'CS 3345'")
    subject, number = parts[0].upper(), parts[1]

    result = await nebula.get_best_professor(subject, number)
    if not result:
        return {"professor": None, "a_rate": None}

    return {
        "professor": result["name"],
        "a_rate": result["a_rate"],
        "total_students": result["total_students"],
        "display": f"{result['name']} ({result['a_rate']}% A-rate)",
    }
```

Register this router in `main.py` with prefix `/api/courses`.

#### Frontend (`app/session/page.tsx`):
```typescript
const fetchProfessorForCourse = async (courseCode: string) => {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/courses/${encodeURIComponent(courseCode)}/professor`
    );
    if (!res.ok) return;
    const data = await res.json();
    if (!data.professor) return;

    setColumns(prev => {
      const updated = { ...prev };
      for (const key of Object.keys(updated)) {
        updated[key] = {
          ...updated[key],
          courses: updated[key].courses.map((c: any) =>
            c.code === courseCode ? { ...c, professor: data.display, aRate: data.a_rate } : c
          ),
        };
      }
      return updated;
    });
  } catch {}
};
```

Call `fetchProfessorForCourse(code)` inside `extractAndAddCourses()` after pushing to columns, and inside `buildColumnsFromPlan()`.

#### Course Card UI (`components/dnd-board.tsx`) — add below the title:
```tsx
{course.professor && course.professor !== "TBD" && course.professor !== "Loading..." && (
  <p className="text-[10px] text-violet-300/70 font-medium mt-1 truncate">
    👤 {course.professor}
  </p>
)}
{course.aRate && (
  <div className="w-full h-1 rounded-full bg-white/5 mt-1 overflow-hidden">
    <div
      className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400"
      style={{ width: `${Math.min(course.aRate, 100)}%` }}
    />
  </div>
)}
```

---

### 5. Course Catalog & Prerequisite Data from Nebula Labs

**Current behavior**: `combinedDB.courses.json` missing → 0 courses loaded at backend startup.

#### Update `advisorai/backend/services/data_loader.py`:

```python
import os, json, httpx, asyncio, logging
from datetime import datetime, timedelta
from pathlib import Path

NEBULA_BASE = "https://api.utdnebula.com"
HEADERS = {"x-api-key": os.getenv("NEBULA_API_KEY", "")}
DATA_DIR = Path(__file__).parent.parent / "data"
COURSES_CACHE = DATA_DIR / "combinedDB.courses.json"
CACHE_TTL = timedelta(days=7)

SUBJECTS = ["CS", "SE", "CE", "EE", "MATH", "STAT", "PHYS", "CGS", "COGS", "RHET", "GOVT", "ECS"]

logger = logging.getLogger(__name__)

async def fetch_subject_courses(client: httpx.AsyncClient, subject: str) -> list[dict]:
    courses, offset = [], 0
    while True:
        resp = await client.get(
            f"{NEBULA_BASE}/course",
            params={"subject_prefix": subject, "offset": offset},
            headers=HEADERS,
        )
        if resp.status_code != 200:
            break
        batch = resp.json().get("data", [])
        if not batch:
            break
        courses.extend(batch)
        if len(batch) < 20:
            break
        offset += len(batch)
    return courses

async def fetch_all_courses() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [fetch_subject_courses(client, s) for s in SUBJECTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [c for r in results if isinstance(r, list) for c in r]

def is_stale(path: Path) -> bool:
    if not path.exists():
        return True
    return datetime.now() - datetime.fromtimestamp(path.stat().st_mtime) > CACHE_TTL

def load_courses() -> list[dict]:
    DATA_DIR.mkdir(exist_ok=True)
    if not is_stale(COURSES_CACHE):
        logger.info("Loading courses from cache")
        with open(COURSES_CACHE) as f:
            return json.load(f)
    try:
        logger.info("Fetching courses from Nebula Labs...")
        courses = asyncio.run(fetch_all_courses())
        if courses:
            with open(COURSES_CACHE, "w") as f:
                json.dump(courses, f)
            logger.info(f"Cached {len(courses)} courses")
            return courses
    except Exception as e:
        logger.warning(f"Nebula fetch failed: {e}. Using hardcoded fallback.")
    from .degree_plans import get_fallback_courses
    return get_fallback_courses()
```

#### Hardcoded Fallback (`advisorai/backend/services/degree_plans.py`):

```python
CS_PREREQ_CHAIN = {
    "CS 1136": [],
    "CS 1337": ["CS 1136"],
    "CS 2305": ["CS 1337"],
    "CS 2336": ["CS 1337"],
    "CS 3305": ["CS 2305"],
    "CS 3341": ["MATH 2419"],
    "CS 3345": ["CS 2305", "CS 2336"],
    "CS 3354": ["CS 2336"],
    "CS 4337": ["CS 3345"],
    "CS 4347": ["CS 3345"],
    "CS 4348": ["CS 3345"],
    "CS 4349": ["CS 3305", "CS 3345"],
    "CS 4354": ["CS 3354"],
    "CS 4361": ["CS 3354"],
    "CS 4375": ["CS 3354"],
    "CS 4384": ["CS 3345"],
    "CS 4389": ["CS 3345"],
    "CS 4485": ["CS 3354", "CS 4348"],
    "MATH 2413": [],
    "MATH 2414": ["MATH 2413"],
    "MATH 2419": ["MATH 2414"],
    "MATH 2418": [],
}

CS_CORE_REQUIREMENTS = [
    "CS 1136", "CS 1337", "CS 2305", "CS 2336", "CS 3305",
    "CS 3341", "CS 3345", "CS 3354", "CS 4141", "CS 4337",
    "CS 4348", "CS 4349", "CS 4384", "CS 4485",
]

MATH_REQUIREMENTS = ["MATH 2413", "MATH 2414", "MATH 2418", "MATH 2419"]

TOTAL_DEGREE_HOURS = 124
```

---

### 6. Concise Mode — Reduce Advisor Verbosity

**Immediate fix** — tighten the base `CHAT_SYSTEM_PROMPT` in `services/llm.py`:

Replace:
```
"Keep responses to 2-5 sentences unless the student asks for detail."
```
With:
```
"Keep responses to 1-2 sentences MAXIMUM. Speak like a text message, not an email.
Do not repeat what the student just said. Never start with 'Great question!', 'Sure!', or 'Of course!'.
Get straight to the point. No filler phrases."
```

#### Concise Mode Toggle

**Frontend** (`app/session/page.tsx`):
```typescript
const [conciseMode, setConciseMode] = useState(true); // default ON for voice

// Top-right toggle button:
<button
  onClick={() => setConciseMode(p => !p)}
  className="fixed top-6 right-6 px-3 py-1.5 rounded-full border border-white/10 text-xs text-muted-foreground hover:border-violet-400/40 transition-all"
>
  {conciseMode ? "⚡ Concise" : "💬 Detailed"}
</button>

// In chat POST body:
body: JSON.stringify({ message, history, transcript_context, concise: conciseMode })
```

**Backend** (`routers/voice.py`):
```python
class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    transcript_context: Optional[str] = None
    concise: bool = True   # default ON
```

**Backend** (`services/llm.py`, `chat_with_advisor()`):
```python
async def chat_with_advisor(history, message, transcript_context=None, concise=True):
    system = CHAT_SYSTEM_PROMPT
    if concise:
        system += (
            "\n\nCONCISE MODE ACTIVE: Reply in 1-2 sentences MAX. "
            "No pleasantries. No elaboration. Be direct.\n"
            "Good: 'You still need CS 4348 and CS 4349. Want me to add those?'\n"
            "Bad: 'Great question! Based on your transcript, I can see you have completed...'"
        )
    ...
```

---

### 7. GPA-Aware Course Advising

**Goal**: The advisor should know the student's GPA from their transcript and use it to avoid recommending overloaded or overly difficult semesters — e.g., don't put CS 4349 + CS 4348 + CS 4384 all in the same semester for a 2.4 GPA student.

#### Step 1 — Extract GPA from Transcript (`advisorai/backend/services/transcript_parser.py`)

When parsing the PDF transcript, extract the cumulative GPA. Look for patterns like:
- `"Cum GPA: 3.45"`, `"Cumulative GPA 3.45"`, `"Overall GPA: 3.45"`

```python
import re

def extract_gpa(text: str) -> float | None:
    patterns = [
        r"cum(?:ulative)?\s+gpa[:\s]+(\d\.\d{1,3})",
        r"overall\s+gpa[:\s]+(\d\.\d{1,3})",
        r"gpa[:\s]+(\d\.\d{1,3})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None
```

Add `gpa: float | None` to the parsed transcript response so it flows through to the session context.

#### Step 2 — Pass GPA in Session Context

`advisorai/backend/routers/voice.py` — include `gpa` in `transcript_context` string passed to `chat_with_advisor()`:

```python
# When building transcript_context string, append:
if transcript.gpa:
    transcript_context += f"\nStudent GPA: {transcript.gpa:.2f}"
```

Also add `gpa: float | None` to `FullPlanRequest` so the full-plan endpoint gets it too.

#### Step 3 — Course Difficulty Tiers

Add to `advisorai/backend/services/degree_plans.py`:

```python
# Difficulty tier 1 = manageable, 3 = known to be brutal
COURSE_DIFFICULTY = {
    # Tier 1 — straightforward or lighter workload
    "CS 1136": 1, "CS 1337": 1, "CS 2305": 1, "CS 2336": 1,
    "CS 3354": 1, "CS 4141": 1,
    # Tier 2 — moderate
    "CS 3305": 2, "CS 3341": 2, "CS 4337": 2, "CS 4347": 2,
    "CS 4354": 2, "CS 4361": 2, "CS 4375": 2, "CS 4389": 2,
    # Tier 3 — difficult / high failure rate
    "CS 3345": 3, "CS 4348": 3, "CS 4349": 3, "CS 4384": 3,
    "CS 4485": 3,
    # Math
    "MATH 2413": 2, "MATH 2414": 2, "MATH 2418": 2, "MATH 2419": 3,
}

def get_semester_difficulty_score(course_codes: list[str]) -> int:
    """Sum of difficulty tiers for all courses in a semester."""
    return sum(COURSE_DIFFICULTY.get(c, 2) for c in course_codes)

# GPA thresholds for max difficulty score per semester
# e.g. a 2.5 GPA student shouldn't have a difficulty score > 8
GPA_MAX_DIFFICULTY = {
    # (min_gpa, max_gpa): max_difficulty_per_semester
    (3.5, 4.0): 14,   # high achiever — no restrictions
    (3.0, 3.5): 11,   # solid — avoid stacking 3 tier-3 courses
    (2.5, 3.0): 9,    # average — max 1 tier-3 per semester
    (0.0, 2.5): 7,    # struggling — protect from overloading
}

def get_max_difficulty_for_gpa(gpa: float) -> int:
    for (low, high), max_diff in GPA_MAX_DIFFICULTY.items():
        if low <= gpa <= high:
            return max_diff
    return 9  # safe default
```

#### Step 4 — Inject GPA Context into System Prompt (`services/llm.py`)

In `generate_full_plan()` and `chat_with_advisor()`, dynamically add GPA guidance:

```python
def build_gpa_guidance(gpa: float | None) -> str:
    if gpa is None:
        return ""
    if gpa >= 3.5:
        return (
            f"\nStudent GPA: {gpa:.2f} (strong). "
            "They can handle a full 15-credit load including difficult courses. "
            "Feel free to recommend challenging upper-division courses together."
        )
    elif gpa >= 3.0:
        return (
            f"\nStudent GPA: {gpa:.2f} (above average). "
            "Limit to 1-2 notoriously difficult courses per semester (e.g. CS 3345, CS 4348, CS 4349). "
            "Pair hard courses with lighter electives."
        )
    elif gpa >= 2.5:
        return (
            f"\nStudent GPA: {gpa:.2f} (average). "
            "Do NOT put more than one of [CS 3345, CS 4348, CS 4349, CS 4384, MATH 2419] in the same semester. "
            "Prioritize grade recovery — recommend courses where the student is likely to earn an A. "
            "Consider suggesting 12 credit hours (4 courses) instead of 15 for tough semesters."
        )
    else:
        return (
            f"\nStudent GPA: {gpa:.2f} (needs improvement). "
            "IMPORTANT: Protect their GPA. Recommend only 12 credit hours per semester. "
            "Avoid all tier-3 difficulty courses until GPA improves above 2.5. "
            "Suggest courses known for high A-rates first. "
            "Explicitly mention the academic standing risk if they overload."
        )
```

Append `build_gpa_guidance(gpa)` to the system prompt in both `chat_with_advisor()` and the full-plan generation prompt.

#### Step 5 — Validate Difficulty in `generate_full_plan()` (`services/llm.py`)

After parsing Gemini's JSON response, run a difficulty check per semester:

```python
def validate_semester_difficulty(sem: SemesterPlan, gpa: float | None) -> SemesterPlan:
    if gpa is None or gpa >= 3.5:
        return sem  # no restrictions for high GPA
    
    max_diff = get_max_difficulty_for_gpa(gpa)
    course_codes = [c.code for c in sem.courses]
    score = get_semester_difficulty_score(course_codes)
    
    if score <= max_diff:
        return sem
    
    # Sort courses by difficulty descending, remove hardest ones until under limit
    sem.courses.sort(key=lambda c: COURSE_DIFFICULTY.get(c.code, 2), reverse=True)
    while get_semester_difficulty_score([c.code for c in sem.courses]) > max_diff and sem.courses:
        removed = sem.courses.pop(0)  # remove hardest course
        sem.total_credits -= removed.credits
    
    return sem
```

#### Step 6 — Frontend Display (`app/session/page.tsx` + `components/dnd-board.tsx`)

- When displaying the GPA in the session, show it in the transcript summary panel
- In the DND board, if a semester's difficulty score is too high for the GPA, show a warning tooltip on the column header: `"⚠ Heavy semester for your GPA"`

---

## Summary of All Files to Create / Modify

| File | Action | What changes |
|------|--------|-------------|
| `app/session/page.tsx` | Modify | `isPlayingRef` audio guard, "Generate My Plan" button, `buildColumnsFromPlan()`, concise toggle, `fetchProfessorForCourse()` |
| `components/dnd-board.tsx` | Modify | Credit warning badge per column, professor A-rate bar on cards |
| `advisorai/backend/routers/voice.py` | Modify | Add `concise: bool` to `ChatRequest` |
| `advisorai/backend/routers/recommend.py` | Modify | Add `POST /api/recommend/full-plan` endpoint + models |
| `advisorai/backend/routers/courses.py` | Modify | Add `GET /api/courses/{code}/professor` endpoint |
| `advisorai/backend/main.py` | Modify | Register `courses` router with prefix `/api/courses` |
| `advisorai/backend/services/llm.py` | Modify | Tighten `CHAT_SYSTEM_PROMPT`, concise injection, add `generate_full_plan()` |
| `advisorai/backend/services/data_loader.py` | Modify | Async Nebula fetch on startup, 7-day cache, fallback |
| `advisorai/backend/services/nebula.py` | **CREATE** | `get_best_professor()` via `/course/sections/trends` |
| `advisorai/backend/services/degree_plans.py` | Modify | Add `CS_PREREQ_CHAIN`, `CS_CORE_REQUIREMENTS`, `TOTAL_DEGREE_HOURS`, `COURSE_DIFFICULTY`, `GPA_MAX_DIFFICULTY` |
| `advisorai/backend/services/transcript_parser.py` | Modify | Extract `gpa` via regex from PDF text, include in parsed result |
| `advisorai/backend/services/llm.py` | Modify | Add `build_gpa_guidance()`, `validate_semester_difficulty()`, inject into both prompts |
| `advisorai/backend/data/` | Create dir | Cache directory for JSON files |

---

## Environment Variables Required

```env
# Backend (advisorai/backend/.env)
GEMINI_API_KEY=...         # Read by services/llm.py
GOOGLE_API_KEY=...         # Same value as GEMINI_API_KEY (legacy)
NEBULA_API_KEY=...         # x-api-key header for Nebula Labs
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# Frontend (.env.local in project root)
ELEVENLABS_API_KEY=...     # Read by app/api/speak/route.ts
ELEVENLABS_VOICE_ID=...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Implementation Order

1. **Fix audio self-interrupt** — `isPlayingRef` guard, remove premature state sets (15 min)
2. **Tighten system prompt verbosity** — 1-2 sentence default in `CHAT_SYSTEM_PROMPT` (5 min)
3. **Concise mode toggle** — `concise` field + prompt injection + UI toggle (30 min)
4. **Create `services/nebula.py`** — `get_best_professor()` via `/course/sections/trends` (45 min)
5. **Add `GET /api/courses/{code}/professor`** — wire up nebula service, register router (20 min)
6. **Frontend professor badge** — `fetchProfessorForCourse()`, card A-rate bar (30 min)
7. **Update `data_loader.py`** — async Nebula fetch on startup, 7-day TTL cache (45 min)
8. **Hardcoded CS prereq fallback** in `degree_plans.py` (15 min)
9. **Credit hour enforcement** — backend validation + frontend color badges (30 min)
10. **GPA extraction** — regex in `transcript_parser.py`, flow through to session context (20 min)
11. **GPA difficulty tiers** — `COURSE_DIFFICULTY` map + `build_gpa_guidance()` + `validate_semester_difficulty()` (30 min)
12. **Full 4-year plan endpoint** — `POST /api/recommend/full-plan`, Gemini JSON prompt (60 min)
13. **Dynamic board columns** — `buildColumnsFromPlan()` replaces static columns (45 min)
