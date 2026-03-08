"""
transcript_parser.py — UTD Unofficial Transcript PDF Parser

Parses a real UTD unofficial transcript PDF using pdfplumber.
Tested against actual UTD transcript format with columns:
  Course  Description  Attempted  Earned  Grade  Points

Extracts: student name, student ID, major, GPA, total credit hours,
and all completed courses with grades and semester tags.

Returns a TranscriptData object using our Pydantic schemas.
"""

import re
import logging
from io import BytesIO
from typing import Optional

import pdfplumber

from models.schemas import CompletedCourse, TranscriptData

logger = logging.getLogger(__name__)

# ─── Grade constants ───────────────────────────────────────────────
PASSING_GRADES = {
    "A+", "A", "A-",
    "B+", "B", "B-",
    "C+", "C", "C-",
    "D+", "D", "D-",
    "P", "CR", "S",
}
ALL_GRADES = PASSING_GRADES | {"F", "W", "WL", "I", "NP", "NF", "NC", "AU", "WF"}
GRADE_RE = r"[A-F][+-]?|W[LF]?|P|CR|NP|NF|NC|I|S|AU"

# ─── Compiled regex patterns ──────────────────────────────────────

# Student name: "Name: John Doe"
RE_NAME = re.compile(r"Name\s*:\s*(.+)", re.IGNORECASE)

# Student ID: "Student ID: 2021796767"
RE_STUDENT_ID = re.compile(r"Student\s*ID\s*:\s*(\d+)", re.IGNORECASE)

# Major: "Computer Science Major CIP: 11.0101" or "Computer Science Major"
RE_MAJOR = re.compile(
    r":\s*(.+?)\s+Major(?:\s+CIP)?",
    re.IGNORECASE,
)

# Minor: "Cognitive Science Minor"
RE_MINOR = re.compile(
    r":\s*(.+?)\s+Minor",
    re.IGNORECASE,
)

# Semester headers: "2024 Fall", "2025 Spring"
RE_SEMESTER = re.compile(
    r"^(\d{4}\s+(?:Spring|Summer|Fall|Winter))\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# UTD course row: DEPT CODE  DESCRIPTION  Attempted  Earned  Grade  Points
# Example: CS 1200 INTRO TO COMP SCI & SOFTWARE 2.000 2.000 A 8.000
RE_COURSE = re.compile(
    r"^([A-Z]{2,4})\s+(\d{4})\s+"               # dept + number
    r"(.+?)\s+"                                   # course name (non-greedy)
    r"(\d+\.\d{3})\s+"                            # attempted hours
    r"(\d+\.\d{3})\s+"                            # earned hours
    r"(" + GRADE_RE + r")\s+"                     # grade
    r"(\d+\.\d{3})\s*$",                          # quality points
    re.MULTILINE,
)

# In-progress course (no grade yet): DEPT CODE  DESCRIPTION  Attempted  0.000  0.000
# Example: CS 3345 DATA STRUCT & FOUNDATION ALGOR 3.000 0.000 0.000
RE_COURSE_IN_PROGRESS = re.compile(
    r"^([A-Z]{2,4})\s+(\d{4})\s+"
    r"(.+?)\s+"
    r"(\d+\.\d{3})\s+"                            # attempted
    r"0\.000\s+"                                   # earned = 0
    r"0\.000\s*$",                                 # points = 0
    re.MULTILINE,
)

# Transfer course row (same format but may have 0.000 points)
# We handle these with the same RE_COURSE pattern

# Cumulative GPA: "Cum GPA: 3.859" or "Cum GPA 3.859"
RE_CUM_GPA = re.compile(
    r"Cum\s+GPA\s*:?\s*(\d+\.\d+)",
    re.IGNORECASE,
)

# Cumulative totals: "Cum Totals 65.000 50.000 50.000 167.940"
#                     (Attempted  Earned  GPA_Uts  Points)
RE_CUM_TOTALS = re.compile(
    r"Cum\s+Totals?\s+(\d+\.\d+)\s+(\d+\.\d+)",
    re.IGNORECASE,
)

# Combined Cum totals (includes transfer): "Comb Totals 89.000 74.000 ..."
RE_COMBINED_CUM_TOTALS = re.compile(
    r"Combined\s+Cum\s+GPA\s+(\d+\.\d+)\s+Comb\s+Totals?\s+(\d+\.\d+)\s+(\d+\.\d+)",
    re.IGNORECASE,
)


class TranscriptParser:
    """
    Parses a UTD unofficial transcript PDF and extracts structured data.

    Handles:
    - Student info (name, ID)
    - Academic program (major, minor)
    - Transfer credits
    - Completed courses with grades
    - In-progress courses (current semester)
    - Cumulative GPA and total credit hours
    """

    def parse_pdf(self, file_content: bytes) -> TranscriptData:
        """
        Parse a UTD unofficial transcript PDF.

        Args:
            file_content: Raw bytes of the PDF file.

        Returns:
            TranscriptData with all extracted fields.

        Raises:
            ValueError: If the PDF cannot be parsed or critical fields are missing.
        """
        try:
            text = self._extract_text_from_pdf(file_content)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ValueError(f"Could not read the PDF file: {e}")

        if not text.strip():
            raise ValueError(
                "The PDF appears to be empty or contains only images "
                "(no extractable text)."
            )

        return self.parse_text(text)

    def _extract_text_from_pdf(self, content: bytes) -> str:
        """Extract all text from PDF pages using pdfplumber."""
        pages_text = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
        return "\n".join(pages_text)

    def parse_text(self, text: str) -> TranscriptData:
        """
        Parse plain text (extracted from PDF) into TranscriptData.

        Also usable for testing without a real PDF.
        """
        # ── Student info ──
        student_name = self._first_match(RE_NAME, text) or "Unknown Student"
        student_id = self._first_match(RE_STUDENT_ID, text)

        # ── Major ──
        major = self._extract_major(text)

        # ── GPA (take the LAST cumulative GPA — that's the most current) ──
        gpa = self._extract_final_cum_gpa(text)

        # ── Total credit hours ──
        total_hours = self._extract_total_hours(text)

        # ── Courses ──
        courses = self._extract_courses(text)

        # If total hours weren't found in summary, compute from passing courses
        if total_hours == 0.0:
            total_hours = sum(
                c.credit_hours for c in courses
                if c.grade in PASSING_GRADES
            )

        logger.info(
            f"Parsed: {student_name} | {major} | "
            f"GPA {gpa} | {len(courses)} courses | {total_hours} hrs"
        )

        # ── Minor (optional) ──
        minor_match = RE_MINOR.search(text)
        minor = minor_match.group(1).strip() if minor_match else None
        if minor:
            logger.info(f"Minor detected: {minor}")

        return TranscriptData(
            student_name=student_name.strip(),
            student_id=student_id,
            major=major.strip(),
            minor=minor,
            total_credit_hours=total_hours,
            gpa=gpa,
            completed_courses=courses,
        )

    # ─── Field extractors ─────────────────────────────────────────

    def _first_match(self, pattern: re.Pattern, text: str) -> Optional[str]:
        """Return the first capturing group of the first match, or None."""
        m = pattern.search(text)
        return m.group(1).strip() if m else None

    def _extract_major(self, text: str) -> str:
        """
        Extract major from Academic Program History section.
        Looks for lines like "2024-02-04: Computer Science Major CIP: 11.0101"
        Takes the LAST occurrence (most recent program declaration).
        """
        matches = RE_MAJOR.findall(text)
        if matches:
            # Take the last (most recent) major declaration, clean it up
            major = matches[-1].strip()
            # Remove date prefix if present
            major = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", major)
            return major

        # Fallback: look for "Major:" or "Program:" lines
        for pattern in [
            re.compile(r"Major\s*:\s*(.+)", re.IGNORECASE),
            re.compile(r"Program\s*:\s*(.+)", re.IGNORECASE),
        ]:
            m = pattern.search(text)
            if m:
                val = m.group(1).strip()
                # Filter out generic values
                if val.lower() not in ("undergraduate", "graduate"):
                    return val

        return "Undeclared"

    def _extract_final_cum_gpa(self, text: str) -> float:
        """
        Get the LAST cumulative GPA in the transcript.
        UTD transcripts repeat Cum GPA after every semester —
        the last one is the most up-to-date.
        """
        matches = RE_CUM_GPA.findall(text)
        if matches:
            return float(matches[-1])
        return 0.0

    def _extract_total_hours(self, text: str) -> float:
        """
        Extract total earned credit hours.
        Tries Combined Cum Totals first (includes transfers),
        then falls back to Cum Totals.
        """
        # Try Combined Cum (includes transfer credits)
        combined = RE_COMBINED_CUM_TOTALS.findall(text)
        if combined:
            # Last occurrence, second group = attempted, third = earned
            _, attempted, earned = combined[-1]
            return float(earned)

        # Fall back to Cum Totals (UTD-only credits)
        cum = RE_CUM_TOTALS.findall(text)
        if cum:
            attempted, earned = cum[-1]
            return float(earned)

        return 0.0

    def _extract_courses(self, text: str) -> list[CompletedCourse]:
        """
        Extract all courses from transcript text.
        Tracks current semester to tag each course.
        Handles both completed and in-progress courses.
        """
        courses: list[CompletedCourse] = []
        seen: set[tuple[str, str]] = set()
        current_semester: Optional[str] = None

        # Track if we're in the transfer section
        in_transfer_section = False

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # Detect transfer section
            if "Transfer Credit" in stripped:
                in_transfer_section = True
                continue
            if "Beginning of Undergraduate Record" in stripped:
                in_transfer_section = False
                continue

            # Detect semester header: "2024 Fall"
            sem_match = RE_SEMESTER.match(stripped)
            if sem_match:
                current_semester = sem_match.group(1).strip()
                continue

            # Try to parse as a completed course line
            course_match = RE_COURSE.match(stripped)
            if course_match:
                dept, num, name, attempted, earned, grade, points = course_match.groups()
                code = f"{dept} {num}"
                credit_hours = float(attempted)  # Use attempted hours as credit value
                semester_label = current_semester or "Unknown"

                # Tag transfer courses
                if in_transfer_section:
                    semester_label = f"{current_semester} (Transfer)" if current_semester else "Transfer"

                key = (code, semester_label)
                if key not in seen:
                    seen.add(key)
                    courses.append(CompletedCourse(
                        course_code=code,
                        course_name=name.strip(),
                        grade=grade.strip(),
                        credit_hours=credit_hours,
                        semester=semester_label,
                    ))
                continue

            # Try to parse as an in-progress course (no grade)
            ip_match = RE_COURSE_IN_PROGRESS.match(stripped)
            if ip_match:
                dept, num, name, attempted = ip_match.groups()
                code = f"{dept} {num}"
                semester_label = current_semester or "Current"
                key = (code, semester_label)
                if key not in seen:
                    seen.add(key)
                    courses.append(CompletedCourse(
                        course_code=code,
                        course_name=name.strip(),
                        grade="IP",  # In Progress
                        credit_hours=float(attempted),
                        semester=semester_label,
                    ))

        return courses

    def parse(self, file_content: bytes, filename: str) -> TranscriptData:
        """
        Convenience: parse by file extension.

        Args:
            file_content: Raw bytes of the file.
            filename: Original filename.

        Returns:
            TranscriptData with all extracted fields.
        """
        if filename.lower().endswith(".pdf"):
            return self.parse_pdf(file_content)
        elif filename.lower().endswith(".txt"):
            return self.parse_text(file_content.decode("utf-8"))
        else:
            raise ValueError(
                f"Unsupported file format: {filename}. "
                "Please upload a PDF or TXT transcript."
            )


# ─── Utility functions ────────────────────────────────────────────

def extract_completed_course_codes(transcript: TranscriptData) -> list[str]:
    """
    Get a flat list of passed course codes.
    Excludes W, F, IP, and other non-passing grades.
    """
    return [
        c.course_code
        for c in transcript.completed_courses
        if c.grade in PASSING_GRADES
    ]


def get_courses_by_semester(transcript: TranscriptData) -> dict[str, list[CompletedCourse]]:
    """
    Group completed courses by semester.
    Useful for timeline visualization on the frontend.
    """
    semesters: dict[str, list[CompletedCourse]] = {}
    for course in transcript.completed_courses:
        sem = course.semester or "Unknown"
        semesters.setdefault(sem, []).append(course)
    return semesters


def get_in_progress_courses(transcript: TranscriptData) -> list[CompletedCourse]:
    """Get courses currently in progress (grade = 'IP')."""
    return [c for c in transcript.completed_courses if c.grade == "IP"]
