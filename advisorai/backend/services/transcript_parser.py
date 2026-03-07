import re
from typing import List, Dict, Any
from io import BytesIO

# Optional: PDF parsing
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class TranscriptParser:
    """Parse academic transcripts to extract course history."""

    def parse(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Parse transcript file and extract course information."""
        if filename.endswith(".pdf"):
            return self.parse_pdf(file_content)
        elif filename.endswith(".txt"):
            return self.parse_text(file_content.decode("utf-8"))
        else:
            raise ValueError(f"Unsupported file format: {filename}")

    def parse_pdf(self, content: bytes) -> Dict[str, Any]:
        """Parse PDF transcript."""
        if not HAS_PYPDF:
            raise ImportError("pypdf is required for PDF parsing")

        reader = pypdf.PdfReader(BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return self.parse_text(text)

    def parse_text(self, text: str) -> Dict[str, Any]:
        """Parse plain text transcript."""
        courses = []

        # Common transcript patterns
        # Example: "CS 1337    Computer Science I    A    3.00"
        course_pattern = r"([A-Z]{2,4})\s*(\d{4})\s+(.+?)\s+([A-F][+-]?|W|P|CR)\s+(\d+\.?\d*)"

        matches = re.findall(course_pattern, text)

        for match in matches:
            dept, number, name, grade, credits = match
            courses.append({
                "code": f"{dept} {number}",
                "name": name.strip(),
                "grade": grade,
                "credits": float(credits),
            })

        # Extract GPA if present
        gpa_pattern = r"(?:GPA|Grade Point Average)[:\s]+(\d+\.\d+)"
        gpa_match = re.search(gpa_pattern, text, re.IGNORECASE)
        gpa = float(gpa_match.group(1)) if gpa_match else None

        return {
            "courses": courses,
            "gpa": gpa,
            "total_credits": sum(c["credits"] for c in courses),
        }


def extract_completed_courses(transcript_data: Dict[str, Any]) -> List[str]:
    """Extract list of completed course codes from parsed transcript."""
    passing_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "P", "CR"}

    return [
        course["code"]
        for course in transcript_data.get("courses", [])
        if course["grade"] in passing_grades
    ]
