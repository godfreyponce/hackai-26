"""
data_loader.py — Load and index UTD course catalog from Nebula API data.

Reads combinedDB.courses.json and combinedDB.degrees.json,
deduplicates by latest catalog year, and provides fast lookups.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


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
        """Load and dedupe courses from combinedDB.courses.json."""
        path = os.path.join(DATA_DIR, "combinedDB.courses.json")
        if not os.path.exists(path):
            logger.warning(f"Courses file not found: {path}")
            return

        logger.info(f"Loading courses from {path}...")
        with open(path, "r") as f:
            raw_courses = json.load(f)

        # Dedupe: keep latest catalog_year per course code
        best: dict[str, dict] = {}
        for c in raw_courses:
            code = f"{c['subject_prefix']} {c['course_number']}"
            year = c.get("catalog_year", "0")
            if code not in best or year > best[code].get("catalog_year", "0"):
                best[code] = c

        # Build lookups
        for code, data in best.items():
            info = CourseInfo(data)
            self.courses[code] = info
            if info.internal_course_number:
                self.by_internal_id[info.internal_course_number] = code

        # Also build a reverse map for ALL internal IDs (not just latest)
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
