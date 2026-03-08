"""
data_loader.py — Load and index UTD course catalog from Nebula API data.

Fetches from Nebula Labs API if local cache is missing or stale,
deduplicates by latest catalog year, and provides fast lookups.
"""

import json
import logging
import os
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
NEBULA_BASE = "https://api.utdnebula.com"
CACHE_TTL = timedelta(days=7)

# Subject prefixes to fetch from Nebula
SUBJECTS = ["CS", "SE", "CE", "EE", "MATH", "STAT", "PHYS", "CGS", "COGS", "RHET", "GOVT", "ECS", "ENGR", "BMEN", "MECH", "FIN", "BA", "MKT", "ACCT", "MIS", "OBHR", "OPRE", "IMS", "HIST", "HUMA", "ARTS", "ECON", "PSY", "SOC", "COMM", "ATCM", "BIOL", "CHEM", "GEOS", "NATS"]


def _get_nebula_headers() -> dict:
    """Get headers for Nebula API requests."""
    api_key = os.environ.get("NEBULA_API_KEY", "")
    return {"x-api-key": api_key} if api_key else {}


async def _fetch_subject_courses(client: httpx.AsyncClient, subject: str) -> list[dict]:
    """Fetch all courses for a single subject prefix."""
    courses = []
    offset = 0
    while True:
        try:
            resp = await client.get(
                f"{NEBULA_BASE}/course",
                params={"subject_prefix": subject, "offset": offset},
                headers=_get_nebula_headers(),
                timeout=30.0,
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            batch = data.get("data", [])
            if not batch:
                break
            courses.extend(batch)
            if len(batch) < 20:
                break
            offset += len(batch)
        except Exception as e:
            logger.warning(f"Failed to fetch {subject} courses: {e}")
            break
    return courses


async def _fetch_all_courses() -> list[dict]:
    """Fetch courses from Nebula API for all subject prefixes."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = [_fetch_subject_courses(client, s) for s in SUBJECTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_courses = []
    for r in results:
        if isinstance(r, list):
            all_courses.extend(r)
    return all_courses


def _is_cache_stale(path: str) -> bool:
    """Check if the cache file is missing or older than TTL."""
    if not os.path.exists(path):
        return True
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime > CACHE_TTL


def fetch_and_cache_courses() -> list[dict]:
    """Fetch courses from Nebula API and cache to disk. For use outside an event loop."""
    os.makedirs(DATA_DIR, exist_ok=True)
    cache_path = os.path.join(DATA_DIR, "combinedDB.courses.json")

    # Return cached if fresh
    if not _is_cache_stale(cache_path):
        logger.info("Using cached course data")
        with open(cache_path, "r") as f:
            return json.load(f)

    # Fetch from API
    logger.info("Fetching courses from Nebula Labs API...")
    try:
        # Check if we're inside a running event loop
        try:
            loop = asyncio.get_running_loop()
            # We are inside a running loop — cannot use asyncio.run()
            # Return empty and let the async variant handle it
            logger.info("Inside running loop, deferring to async fetch")
            return []
        except RuntimeError:
            # No running loop — safe to use asyncio.run()
            courses = asyncio.run(_fetch_all_courses())
            if courses:
                with open(cache_path, "w") as f:
                    json.dump(courses, f)
                logger.info(f"Cached {len(courses)} courses to {cache_path}")
                return courses
    except Exception as e:
        logger.error(f"Failed to fetch from Nebula: {e}")

    # Try to load stale cache as fallback
    if os.path.exists(cache_path):
        logger.warning("Using stale cache as fallback")
        with open(cache_path, "r") as f:
            return json.load(f)

    return []


async def fetch_and_cache_courses_async() -> list[dict]:
    """Async version for use inside a running event loop (e.g. uvicorn startup)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    cache_path = os.path.join(DATA_DIR, "combinedDB.courses.json")

    if not _is_cache_stale(cache_path):
        logger.info("Using cached course data")
        with open(cache_path, "r") as f:
            return json.load(f)

    logger.info("Fetching courses from Nebula Labs API (async)...")
    try:
        courses = await _fetch_all_courses()
        if courses:
            with open(cache_path, "w") as f:
                json.dump(courses, f)
            logger.info(f"Cached {len(courses)} courses to {cache_path}")
            return courses
    except Exception as e:
        logger.error(f"Failed to fetch from Nebula: {e}")

    if os.path.exists(cache_path):
        logger.warning("Using stale cache as fallback")
        with open(cache_path, "r") as f:
            return json.load(f)

    return []


class CourseInfo:
    """Lightweight course info for fast lookup."""
    __slots__ = [
        "code", "title", "credits", "description",
        "enrollment_reqs", "prerequisites_raw",
        "internal_course_number", "school", "class_level",
    ]

    def __init__(self, data: dict):
        self.code = f"{data['subject_prefix']} {data['course_number']}"
        self.title = data.get("title", "")
        try:
            self.credits = int(data.get("credit_hours", "3"))
        except (ValueError, TypeError):
            self.credits = 0
        self.description = data.get("description", "")
        self.enrollment_reqs = data.get("enrollment_reqs", "")
        self.prerequisites_raw = data.get("prerequisites")
        self.internal_course_number = data.get("internal_course_number", "")
        self.school = data.get("school", "")
        self.class_level = data.get("class_level", "")


class CourseDataStore:
    """
    In-memory store of UTD course catalog.
    Deduplicates courses by latest catalog year.
    Provides lookups by code and internal number.
    """

    def __init__(self):
        self.courses: dict[str, CourseInfo] = {}          # "CS 1337" -> CourseInfo
        self.by_internal_id: dict[str, str] = {}          # "016285" -> "CS 1436"
        self.degrees: list[dict] = []                     # Degree metadata
        self._loaded = False

    def load(self):
        """Load data from JSON files. Call once at startup."""
        if self._loaded:
            return

        self._load_courses()
        self._load_degrees()
        self._loaded = True

    def _load_courses(self):
        """Load and dedupe courses from combinedDB.courses.json or fetch from API."""
        path = os.path.join(DATA_DIR, "combinedDB.courses.json")

        # Try to load from cache first
        if not _is_cache_stale(path):
            logger.info(f"Loading courses from {path}...")
            with open(path, "r") as f:
                raw_courses = json.load(f)
        else:
            raw_courses = fetch_and_cache_courses()

        if not raw_courses:
            logger.warning("No courses loaded - check Nebula API key")
            return

        # Dedupe: keep latest catalog_year per course code
        best: dict[str, dict] = {}
        best_internal: dict[str, dict] = {}
        for c in raw_courses:
            code = f"{c['subject_prefix']} {c['course_number']}"
            year = c.get("catalog_year", "0")
            if code not in best or year > best[code].get("catalog_year", "0"):
                best[code] = c

            icn = c.get("internal_course_number", "")
            if icn:
                if icn not in best_internal or year > best_internal[icn].get("catalog_year", "0"):
                    best_internal[icn] = c

        # Build lookups
        for code, data in best.items():
            info = CourseInfo(data)
            self.courses[code] = info
        for icn, data in best_internal.items():
            code = f"{data['subject_prefix']} {data['course_number']}"
            self.by_internal_id[icn] = code

        # Also build a reverse map for any internal IDs missing from latest mapping
        for c in raw_courses:
            icn = c.get("internal_course_number", "")
            if icn and icn not in self.by_internal_id:
                self.by_internal_id[icn] = f"{c['subject_prefix']} {c['course_number']}"

        logger.info(f"Loaded {len(self.courses)} unique courses, {len(self.by_internal_id)} internal ID mappings")

    def _load_degrees(self):
        """Load degree metadata from combinedDB.degrees.json."""
        path = os.path.join(DATA_DIR, "combinedDB.degrees.json")
        if not os.path.exists(path):
            logger.warning(f"Degrees file not found: {path}")
            return

        with open(path, "r") as f:
            self.degrees = json.load(f)

        logger.info(f"Loaded {len(self.degrees)} degree programs")

    def get_course(self, code: str) -> Optional[CourseInfo]:
        """Look up a course by code (e.g., 'CS 1337')."""
        return self.courses.get(code)

    def resolve_internal_id(self, internal_id: str) -> Optional[str]:
        """Resolve an internal course number to a course code."""
        return self.by_internal_id.get(internal_id)

    def get_prerequisites(self, code: str) -> list[str]:
        """
        Get flat list of prerequisite course codes for a course.
        Recursively resolves the prereq tree from Nebula format.
        """
        course = self.get_course(code)
        if not course or not course.prerequisites_raw:
            return []

        prereq_codes = set()
        self._extract_prereq_codes(course.prerequisites_raw, prereq_codes)
        return sorted(prereq_codes)

    def _extract_prereq_codes(self, node: dict, result: set):
        """Recursively extract course codes from Nebula prerequisite tree."""
        if not isinstance(node, dict):
            return

        node_type = node.get("type", "")

        if node_type == "course":
            ref = node.get("class_reference", "")
            code = None
            if isinstance(ref, str):
                ref = ref.strip().upper()
                direct_match = re.match(r"^([A-Z]{2,4})\s*(\d{4})$", ref)
                if direct_match:
                    code = f"{direct_match.group(1)} {direct_match.group(2)}"
            if not code:
                code = self.resolve_internal_id(ref)
            if code:
                result.add(code)

        elif node_type in ("collection", "choice"):
            for opt in node.get("options", []):
                self._extract_prereq_codes(opt, result)
            # Also check "choices" key (used in choice type)
            choices = node.get("choices")
            if choices:
                self._extract_prereq_codes(choices, result)

    def search_courses(self, query: str, limit: int = 20) -> list[CourseInfo]:
        """Simple text search across course codes and titles."""
        query_lower = query.lower()
        results = []
        for code, info in self.courses.items():
            if (query_lower in code.lower() or
                query_lower in info.title.lower() or
                query_lower in info.description.lower()):
                results.append(info)
                if len(results) >= limit:
                    break
        return results


# ─── Singleton ─────────────────────────────────────────────────────
_store: Optional[CourseDataStore] = None


def get_course_store() -> CourseDataStore:
    """Get or create the singleton CourseDataStore."""
    global _store
    if _store is None:
        _store = CourseDataStore()
        _store.load()
    return _store
