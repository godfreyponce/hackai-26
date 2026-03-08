"""
Nebula Labs API client.
Docs: https://api.utdnebula.com/swagger/index.html
Repo: https://github.com/UTDNebula/nebula-api

Endpoints used:
  GET /course                     — all courses (subject_prefix, course_number, title, credit_hours, prerequisites)
  GET /course/{id}/professors     — professor IDs for a course
  GET /course/{id}/sections       — section meeting times
  GET /professor/{id}/grades      — grade distribution to compute avg_grade + consistency

API key set via NEBULA_API_KEY env var, passed as header: x-api-key

Schema notes (from nebula-api repo):
- Course.prerequisites is a CollectionRequirement with nested options containing CourseRequirement objects
- CourseRequirement has 'class_reference' field (e.g., "CS 2305")
- Meeting uses 'meeting_days' (not 'days')
- GradeDistribution is [14]int: [A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W]
- Section does NOT have an 'enrollment' field in the API schema
"""

import asyncio
import logging
import os
import re
import statistics
import httpx

from models.schemas import NebulaCourse, NebulaProfessor, NebulaSection

logger = logging.getLogger(__name__)

BASE_URL = "https://api.utdnebula.com"
API_KEY = os.environ.get("NEBULA_API_KEY", "")

# Grade points for GPA calculation
# Nebula grade_distribution index order: [A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W]
# Total: 14 elements
GRADE_POINTS = [4.0, 4.0, 3.7, 3.3, 3.0, 2.7, 2.3, 2.0, 1.7, 1.3, 1.0, 0.7, 0.0, 0.0]
GRADE_LABELS = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "W"]


def _headers() -> dict:
    """Return headers for Nebula API requests."""
    if not API_KEY:
        logger.warning("NEBULA_API_KEY not set - API calls may fail")
    return {"x-api-key": API_KEY}


def _parse_credits(credit_hours_str: str) -> int:
    """Parse '3 semester credit hours' -> 3. Defaults to 3 if unparseable."""
    if not credit_hours_str:
        return 3
    match = re.search(r"(\d+)", str(credit_hours_str))
    return int(match.group(1)) if match else 3


def _parse_prereqs(prereqs_obj: dict | None) -> list[str]:
    """
    Flatten Nebula's nested prerequisites CollectionRequirement into a simple list of course ID strings.

    Nebula prereqs structure:
    {
        "type": "collection",
        "options": [
            {"type": "course", "class_reference": "CS 2305", "minimum_grade": ""},
            {"type": "collection", "options": [...], ...}
        ]
    }

    We extract ALL leaf course IDs (treats every branch as required — conservative filter).
    """
    if not prereqs_obj:
        return []
    results = []

    def _walk(node):
        if isinstance(node, dict):
            # Check for course requirement with class_reference
            if node.get("type") == "course" and "class_reference" in node:
                class_ref = node["class_reference"]
                if class_ref:
                    results.append(class_ref)
            # Also check old format with subject_prefix + course_number
            elif "subject_prefix" in node and "course_number" in node:
                results.append(f"{node['subject_prefix']} {node['course_number']}")
            # Recurse into options array
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(prereqs_obj)
    return list(set(results))


def _compute_professor_stats(grade_distribution: list[int]) -> tuple[float, float]:
    """
    From Nebula grade_distribution array compute avg_grade (GPA scale 0-4) and
    grade_consistency (0-1, higher = more consistent = tighter distribution).
    Returns (avg_grade, consistency).
    """
    if not grade_distribution:
        return 3.0, 0.5  # sensible defaults

    # Handle both 14-element and shorter arrays
    weighted_points = []
    for i, count in enumerate(grade_distribution[:len(GRADE_POINTS)]):
        if i < len(GRADE_POINTS):
            weighted_points.extend([GRADE_POINTS[i]] * int(count or 0))

    if not weighted_points:
        return 3.0, 0.5

    avg = sum(weighted_points) / len(weighted_points)

    # Consistency: 1 - normalized stdev (stdev of 0 = perfect consistency = 1.0)
    if len(weighted_points) > 1:
        stdev = statistics.stdev(weighted_points)
        # Max possible stdev on 0-4 scale is 2.0
        consistency = max(0.0, 1.0 - (stdev / 2.0))
    else:
        consistency = 1.0

    return round(avg, 3), round(consistency, 3)


def _parse_sections(raw_sections: list[dict], professor_ids: list[str]) -> list[NebulaSection]:
    """Convert Nebula section objects to our NebulaSection schema."""
    sections = []
    for s in raw_sections:
        meetings = s.get("meetings", [])
        if not meetings:
            # Section with no meeting times (e.g., online async)
            sections.append(NebulaSection(
                id=str(s.get("_id", s.get("id", ""))),
                days=[],
                start_time="",
                end_time="",
                professor_id=_get_first_professor_id(s, professor_ids),
                available_seats=None,
                total_seats=None,
            ))
            continue

        meeting = meetings[0]  # Use first meeting for time data

        # API uses 'meeting_days' not 'days'
        days = meeting.get("meeting_days", meeting.get("days", [])) or []
        start = meeting.get("start_time", "") or ""
        end = meeting.get("end_time", "") or ""

        # Note: Section schema doesn't have enrollment info
        # The API doesn't provide seat availability in the section schema
        available = None
        total = None

        sections.append(NebulaSection(
            id=str(s.get("_id", s.get("id", ""))),
            days=days,
            start_time=str(start),
            end_time=str(end),
            professor_id=_get_first_professor_id(s, professor_ids),
            available_seats=available,
            total_seats=total,
        ))
    return sections


def _get_first_professor_id(section: dict, fallback_ids: list[str]) -> str:
    """Extract first professor ID from section or use fallback."""
    prof_ids = section.get("professors", []) or fallback_ids
    if prof_ids:
        # Professor IDs in section are ObjectIDs (strings or dict with $oid)
        first = prof_ids[0]
        if isinstance(first, dict) and "$oid" in first:
            return first["$oid"]
        return str(first)
    return ""


# ============================================================================
# Public API Functions
# ============================================================================

async def get_all_courses() -> list[NebulaCourse]:
    """
    Fetch all courses from Nebula API.
    Uses GET /course/all — returns list of all course objects.
    """
    logger.info("Fetching all courses from Nebula API...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # The API endpoint is /course/all for getting all courses
            resp = await client.get(f"{BASE_URL}/course/all", headers=_headers())
            resp.raise_for_status()
            data = resp.json()
            logger.debug(f"Nebula /course response status: {resp.status_code}")
        except httpx.HTTPError as e:
            logger.error(f"Nebula /course failed: {e}")
            raise

    # Response is {"status": int, "message": str, "data": [...]}
    raw_courses = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(raw_courses, list):
        logger.error(f"Unexpected /course response type: {type(raw_courses)}")
        return []

    courses = []
    seen_ids = set()
    for c in raw_courses:
        try:
            prefix = c.get("subject_prefix", "")
            number = c.get("course_number", "")
            course_id = f"{prefix} {number}".strip()
            if not course_id or course_id == " ":
                continue

            # Deduplicate: Nebula returns multiple entries per course (different semesters)
            if course_id in seen_ids:
                continue
            seen_ids.add(course_id)

            prereqs = _parse_prereqs(c.get("prerequisites"))
            credits = _parse_credits(c.get("credit_hours", "3"))

            # Extract MongoDB ObjectID
            raw_id = c.get("_id", c.get("id", ""))
            if isinstance(raw_id, dict) and "$oid" in raw_id:
                nebula_id = raw_id["$oid"]
            else:
                nebula_id = str(raw_id)

            courses.append(NebulaCourse(
                id=course_id,
                nebula_id=nebula_id,
                name=c.get("title", course_id),
                prereqs=prereqs,
                credits=credits,
                sections=[],        # Fetched separately per course when needed
                professors=[],      # Fetched separately per course when needed
            ))
        except Exception as e:
            logger.warning(f"Failed to parse course {c.get('_id', 'unknown')}: {e}")
            continue

    logger.info(f"Fetched {len(courses)} courses from Nebula API")
    return courses


async def get_professors_for_courses(
    courses: list,
) -> dict[str, list[NebulaProfessor]]:
    """
    For each course, fetch its professors and their grade stats.
    Accepts a list of NebulaCourse objects (uses nebula_id for API calls,
    keys result by human-readable course.id).
    Uses:
      GET /course/{nebula_id}/professors  -> professor IDs
      GET /professor/{id}/grades          -> grade distribution for stats
    Runs requests concurrently per course with rate limiting.
    """
    result: dict[str, list[NebulaProfessor]] = {}

    if not courses:
        return result

    logger.info(f"Fetching professors for {len(courses)} courses...")

    # Limit concurrent requests to avoid overwhelming the API
    semaphore = asyncio.Semaphore(10)

    async def fetch_with_semaphore(client: httpx.AsyncClient, course):
        async with semaphore:
            return await _fetch_professors_for_course(client, course.nebula_id or course.id)

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            fetch_with_semaphore(client, course)
            for course in courses
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    for course, outcome in zip(courses, outcomes):
        if isinstance(outcome, Exception):
            logger.debug(f"Failed to fetch professors for {course.id}: {outcome}")
            result[course.id] = []
        else:
            result[course.id] = outcome

    total_profs = sum(len(v) for v in result.values())
    logger.info(f"Fetched {total_profs} professors for {len(courses)} courses")
    return result


async def _fetch_professors_for_course(
    client: httpx.AsyncClient,
    course_id: str,
) -> list[NebulaProfessor]:
    """Fetch professors for one course and enrich with grade stats."""
    # course_id here is the MongoDB ObjectID
    encoded_id = course_id

    try:
        resp = await client.get(
            f"{BASE_URL}/course/{encoded_id}/professors",
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.debug(f"Nebula /course/{course_id}/professors failed: {e}")
        return []

    raw_profs = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(raw_profs, list):
        return []

    # Fetch grade stats for each professor concurrently
    prof_tasks = [_fetch_professor_with_grades(client, p) for p in raw_profs]
    professors = await asyncio.gather(*prof_tasks, return_exceptions=True)

    return [p for p in professors if isinstance(p, NebulaProfessor)]


async def _fetch_professor_with_grades(
    client: httpx.AsyncClient,
    prof_data: dict,
) -> NebulaProfessor:
    """Build a NebulaProfessor by fetching grade distribution from /professor/{id}/grades."""
    # Handle ObjectID format (could be string or {"$oid": "..."})
    prof_id_raw = prof_data.get("_id", prof_data.get("id", ""))
    if isinstance(prof_id_raw, dict) and "$oid" in prof_id_raw:
        prof_id = prof_id_raw["$oid"]
    else:
        prof_id = str(prof_id_raw)

    first = prof_data.get("first_name", "")
    last = prof_data.get("last_name", "")
    name = f"{first} {last}".strip() or prof_id

    avg_grade, consistency = 3.0, 0.5  # defaults if grades fetch fails

    try:
        resp = await client.get(
            f"{BASE_URL}/professor/{prof_id}/grades",
            headers=_headers(),
        )
        if resp.status_code == 200:
            grade_data = resp.json()
            raw = grade_data.get("data", grade_data) if isinstance(grade_data, dict) else grade_data

            # raw may be a single grade distribution or list of semester grade objects
            distribution = [0] * len(GRADE_POINTS)

            if isinstance(raw, list):
                # Aggregate all semester grade distributions
                for entry in raw:
                    if isinstance(entry, dict):
                        dist = entry.get("grade_distribution", [])
                    else:
                        dist = []
                    for i, count in enumerate(dist[:len(GRADE_POINTS)]):
                        distribution[i] += int(count or 0)
            elif isinstance(raw, dict):
                dist = raw.get("grade_distribution", [])
                for i, count in enumerate(dist[:len(GRADE_POINTS)]):
                    distribution[i] += int(count or 0)

            avg_grade, consistency = _compute_professor_stats(distribution)
    except httpx.HTTPError as e:
        logger.debug(f"Could not fetch grades for professor {prof_id}: {e}")
    except Exception as e:
        logger.debug(f"Error processing grades for professor {prof_id}: {e}")

    return NebulaProfessor(
        id=prof_id,
        name=name,
        avg_grade=avg_grade,
        grade_consistency=consistency,
    )


async def get_best_professor(subject: str, course_number: str) -> dict | None:
    """
    Get the best professor for a course based on A-rate.

    Uses GET /course/sections/trends to get all sections with embedded professor data.
    Aggregates A-rate per professor across all sections.
    Returns the professor with highest A-rate (minimum 30 total students).

    Args:
        subject: Subject prefix (e.g., "CS")
        course_number: Course number (e.g., "3345")

    Returns:
        {"name": str, "a_rate": float, "total_students": int} or None
    """
    # Grade distribution format (14 elements):
    # [A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W]
    # A-rate = (A+ + A + A-) / (total excluding W)
    A_INDICES = [0, 1, 2]  # A+, A, A-

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/course/sections/trends",
                params={"subject_prefix": subject, "course_number": course_number},
                headers=_headers(),
            )
            if resp.status_code != 200:
                logger.debug(f"Nebula /course/sections/trends failed: {resp.status_code}")
                return None

            data = resp.json()
            sections = data.get("data", [])
        except httpx.HTTPError as e:
            logger.debug(f"Nebula trends request failed: {e}")
            return None

    # Aggregate stats per professor
    prof_stats: dict[str, dict] = {}

    for section in sections:
        dist = section.get("grade_distribution", [])
        if len(dist) < 13:  # Need at least A+ through F
            continue

        # Total is sum of grades A+ through F (indices 0-12), excluding W (index 13)
        total = sum(dist[i] for i in range(13) if i < len(dist))
        if total < 5:  # Skip sections with very few students
            continue

        a_grades = sum(dist[i] for i in A_INDICES if i < len(dist))

        for prof in section.get("professor_details", []):
            first = prof.get("first_name", "")
            last = prof.get("last_name", "")
            name = f"{first} {last}".strip()
            if not name:
                continue

            if name not in prof_stats:
                prof_stats[name] = {"a_grades": 0, "total": 0}
            prof_stats[name]["a_grades"] += a_grades
            prof_stats[name]["total"] += total

    # Find professor with highest A-rate (minimum 30 students)
    best = None
    best_rate = -1.0

    for name, stats in prof_stats.items():
        if stats["total"] < 30:
            continue
        rate = stats["a_grades"] / stats["total"]
        if rate > best_rate:
            best_rate = rate
            best = {
                "name": name,
                "a_rate": round(rate * 100, 1),
                "total_students": stats["total"],
            }

    return best


async def get_sections_for_course(course_id: str) -> list[NebulaSection]:
    """
    Fetch sections for a single course.
    Uses GET /course/{id}/sections
    """
    encoded_id = course_id.replace(" ", "%20")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/course/{encoded_id}/sections",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning(f"Nebula /course/{course_id}/sections failed: {e}")
            return []

    raw_sections = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(raw_sections, list):
        return []

    return _parse_sections(raw_sections, [])
