# MOCK DATA for testing – teammate will replace with real UTD flowchart data

# Hardcoded CS degree requirements (upper-division courses only for simplicity)
DEGREE_REQUIREMENTS = {
    "Computer Science": [
        "CS 3341", "CS 3345", "CS 3354", "CS 3377",
        "CS 4341", "CS 4347", "CS 4348", "CS 4349",
        "CS 4365", "CS 4375", "CS 4386", "CS 4391",
        "CS 4485",
    ],
    "Software Engineering": [
        "CS 3341", "CS 3354", "CS 3375", "CS 4354",
        "CS 4365", "CS 4375", "CS 4485",
    ],
}


async def get_degree_requirements(major: str) -> list[str]:
    """Returns hardcoded degree requirements. Teammate will expand with full flowcharts."""
    return DEGREE_REQUIREMENTS.get(major, [])
