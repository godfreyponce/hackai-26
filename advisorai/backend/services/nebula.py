import httpx
from typing import List, Optional
import os

from models.schemas import Course


class NebulaClient:
    """Client for the Nebula API (UTD course data)."""

    def __init__(self):
        self.base_url = os.getenv("NEBULA_API_URL", "https://api.utdnebula.com")
        self.api_key = os.getenv("NEBULA_API_KEY", "")

    async def get_courses(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        level: Optional[int] = None,
    ) -> List[Course]:
        """Fetch courses from Nebula API."""
        async with httpx.AsyncClient() as client:
            params = {}
            if query:
                params["q"] = query
            if department:
                params["department"] = department
            if level:
                params["level"] = level

            response = await client.get(
                f"{self.base_url}/courses",
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()

            data = response.json()
            return [Course(**course) for course in data.get("courses", [])]

    async def get_course(self, course_id: str) -> Course:
        """Fetch a single course by ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/courses/{course_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return Course(**response.json())

    async def get_prerequisites(self, course_id: str) -> dict:
        """Fetch prerequisite tree for a course."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/courses/{course_id}/prerequisites",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            return response.json()
