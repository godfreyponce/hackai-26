"""
degree_plans.py — Hardcoded UTD degree plans for CS, CE, SE.

Each plan defines:
- Required courses by category (prep, core, electives, core curriculum)
- Prerequisite chains (what must be taken before what)
- Total hours required

Parsed from the official UTD degree plan PDFs in data/.
"""

from typing import Optional


# ─── CS Degree Plan (BS, 2025-2026) ───────────────────────────────

CS_DEGREE_PLAN = {
    "name": "Computer Science",
    "degree": "BS",
    "total_hours": 124,
    "categories": {
        "major_introductory": {
            "label": "Major Introductory Courses",
            "hours": 3,
            "courses": ["ECS 1100", "CS 1200"],
            "notes": "First year only — transfer students sub with upper-level tech elective",
        },
        "major_prep": {
            "label": "Major Preparatory Requirements",
            "hours": 42,
            "courses": [
                "MATH 2413",  # or MATH 2417 — Calculus I
                "CS 1436",     # Programming Fundamentals
                "MATH 2414",  # or MATH 2419 — Calculus II
                "CS 1337",     # Computer Science I
                "PHYS 2325",   # Mechanics
                "PHYS 2125",   # Physics Lab I
                "CS 2305",     # Discrete Math I
                "CS 2336",     # or CS 2337 — Computer Science II
                "CS 2340",     # Computer Architecture
                "PHYS 2326",   # Electromagnetism
                "PHYS 2126",   # Physics Lab II
                "MATH 2418",   # Linear Algebra
            ],
            "alternatives": {
                "MATH 2413": ["MATH 2417"],
                "MATH 2414": ["MATH 2419"],
                "CS 2336": ["CS 2337"],
            },
        },
        "major_core": {
            "label": "Major Core Requirements",
            "hours": 39,
            "courses": [
                "CS 3341",    # Probability & Stats
                "CS 3345",    # Data Structures & Algorithms
                "CS 3377",    # C/C++ in UNIX
                "ECS 2390",   # Professional & Technical Communication
                "CS 3354",    # Software Engineering
                "CS 4337",    # Organization of Programming Languages
                "CS 4341",    # Digital Logic & Computer Design
                "CS 4141",    # Digital Systems Lab
                "CS 3162",    # Professional Responsibility
                "CS 4348",    # Operating Systems
                "CS 4349",    # Advanced Algorithm Design
                "CS 4384",    # Automata Theory
                "CS 4347",    # Database Systems
                "CS 4485",    # CS Project
            ],
        },
        "technical_electives": {
            "label": "Technical Electives",
            "hours": 12,
            "courses": [],  # Any CS 4XXX — 4 courses
            "pattern": "CS 4XXX",
            "count": 4,
        },
        "core_curriculum": {
            "label": "State Core Curriculum",
            "hours": 24,
            "courses": [
                "RHET 1302",   # Communication
                "GOVT 2305",   # Government I
                "GOVT 2306",   # Government II
            ],
            "flexible_slots": [
                {"area": "American History (060)", "count": 2},
                {"area": "Language, Philosophy, Culture (040)", "count": 1},
                {"area": "Creative Arts (050)", "count": 1},
                {"area": "Social Behavioral Science (080)", "count": 1},
            ],
        },
        "free_electives": {
            "label": "Free Electives",
            "hours": 10,
            "courses": [],
        },
    },
    "prerequisite_chains": {
        # Math chain
        "MATH 2414": ["MATH 2413"],
        "MATH 2419": ["MATH 2417"],
        "MATH 2418": ["MATH 2414"],
        # Physics chain
        "PHYS 2325": ["MATH 2413"],
        "PHYS 2326": ["PHYS 2325"],
        "PHYS 2125": ["PHYS 2325"],
        "PHYS 2126": ["PHYS 2326"],
        # CS chain - lower division
        "CS 1337": ["CS 1436"],
        "CS 2336": ["CS 1337"],
        "CS 2337": ["CS 1337"],
        "CS 2305": ["CS 1337"],
        "CS 2340": ["CS 2336"],
        # CS chain - upper division
        "CS 3341": ["CS 2305", "MATH 2418"],
        "CS 3345": ["CS 2336", "CS 2305"],
        "CS 3377": ["CS 2336"],
        "CS 3354": ["CS 2336", "CS 3345"],
        "CS 4337": ["CS 2336"],
        "CS 4341": ["CS 2340"],
        "CS 4141": ["CS 4341"],
        "CS 4348": ["CS 3377", "CS 3345"],
        "CS 4349": ["CS 3345"],
        "CS 4384": ["CS 3345"],
        "CS 4347": ["CS 3345"],
        "CS 4485": ["CS 3354"],
        "CS 3162": ["CS 3345"],
        "ECS 2390": ["CS 2336"],
    },
}


# ─── CE Degree Plan (BS, 2025-2026) ───────────────────────────────

CE_DEGREE_PLAN = {
    "name": "Computer Engineering",
    "degree": "BS",
    "total_hours": 129,
    "categories": {
        "major_prep": {
            "label": "Major Preparatory Requirements",
            "hours": 44,
            "courses": [
                "MATH 2413", "MATH 2414", "MATH 2418",
                "PHYS 2325", "PHYS 2125", "PHYS 2326", "PHYS 2126",
                "CS 1436", "CS 1337", "CS 2336", "CS 2340",
                "CE 1100", "CE 1202",
            ],
        },
        "major_core": {
            "label": "Major Core Requirements",
            "hours": 48,
            "courses": [
                "CE 2310", "CE 3201", "CE 3301", "CE 3302",
                "CE 3303", "CE 3320", "CE 3345", "CE 4304",
                "CE 4370", "CE 4388", "CE 4389",
                "CS 3341", "CS 3377", "ECS 2390", "ENGR 3341",
            ],
        },
        "technical_electives": {
            "label": "Technical Electives",
            "hours": 12,
            "courses": [],
            "pattern": "CE/CS/EE 4XXX",
            "count": 4,
        },
    },
    "prerequisite_chains": {
        "CS 1337": ["CS 1436"],
        "CS 2336": ["CS 1337"],
        "CS 2340": ["CS 2336"],
        "MATH 2414": ["MATH 2413"],
        "MATH 2418": ["MATH 2414"],
        "PHYS 2325": ["MATH 2413"],
        "PHYS 2326": ["PHYS 2325"],
        "CE 2310": ["CS 2340", "PHYS 2326"],
        "CE 3301": ["CE 2310"],
        "CE 3302": ["CE 3301"],
        "CE 3303": ["CE 2310"],
        "CS 3345": ["CS 2336", "CS 2305"],
    },
}


# ─── SE Degree Plan (BS, 2025-2026) ───────────────────────────────

SE_DEGREE_PLAN = {
    "name": "Software Engineering",
    "degree": "BS",
    "total_hours": 126,
    "categories": {
        "major_prep": {
            "label": "Major Preparatory Requirements",
            "hours": 42,
            "courses": [
                "MATH 2413", "MATH 2414", "MATH 2418",
                "PHYS 2325", "PHYS 2125", "PHYS 2326", "PHYS 2126",
                "CS 1436", "CS 1337", "CS 2305", "CS 2336", "CS 2340",
                "SE 1100", "SE 1200",
            ],
        },
        "major_core": {
            "label": "Major Core Requirements",
            "hours": 42,
            "courses": [
                "CS 3341", "CS 3345", "CS 3354", "CS 3377",
                "SE 3306", "SE 3340", "SE 3345", "SE 3354",
                "SE 4347", "SE 4348", "SE 4351", "SE 4367",
                "SE 4381", "SE 4485",
                "CS 4337", "CS 4349", "ECS 2390",
            ],
        },
        "technical_electives": {
            "label": "Technical Electives",
            "hours": 12,
            "courses": [],
            "pattern": "CS/SE 4XXX",
            "count": 4,
        },
    },
    "prerequisite_chains": {
        "CS 1337": ["CS 1436"],
        "CS 2336": ["CS 1337"],
        "CS 2340": ["CS 2336"],
        "MATH 2414": ["MATH 2413"],
        "MATH 2418": ["MATH 2414"],
        "CS 3345": ["CS 2336", "CS 2305"],
        "CS 3354": ["CS 2336", "CS 3345"],
        "CS 3377": ["CS 2336"],
        "CS 4349": ["CS 3345"],
        "SE 3354": ["CS 3354"],
        "SE 4485": ["SE 3354"],
    },
}


# ─── Registry ─────────────────────────────────────────────────────

DEGREE_PLANS = {
    "Computer Science": CS_DEGREE_PLAN,
    "computer science": CS_DEGREE_PLAN,
    "CS": CS_DEGREE_PLAN,
    "Computer Engineering": CE_DEGREE_PLAN,
    "computer engineering": CE_DEGREE_PLAN,
    "CE": CE_DEGREE_PLAN,
    "Software Engineering": SE_DEGREE_PLAN,
    "software engineering": SE_DEGREE_PLAN,
    "SE": SE_DEGREE_PLAN,
}


def get_degree_plan(major: str) -> Optional[dict]:
    """
    Look up a degree plan by major name.
    Falls back to CS if major not found (most common at UTD ECS).
    """
    plan = DEGREE_PLANS.get(major)
    if plan:
        return plan

    # Fuzzy match
    major_lower = major.lower()
    for key, plan in DEGREE_PLANS.items():
        if key.lower() in major_lower or major_lower in key.lower():
            return plan

    # Default to CS
    return CS_DEGREE_PLAN


def get_all_required_courses(plan: dict) -> set[str]:
    """Get all explicitly required course codes from a degree plan."""
    required = set()
    for cat in plan["categories"].values():
        required.update(cat.get("courses", []))
    return required


def get_remaining_courses(plan: dict, completed_codes: list[str]) -> dict[str, list[str]]:
    """
    Compute remaining required courses per category.
    Returns { category_key: [remaining_course_codes] }
    """
    completed_set = set(completed_codes)
    remaining = {}

    for cat_key, cat in plan["categories"].items():
        req_courses = cat.get("courses", [])
        alternatives = cat.get("alternatives", {})

        still_needed = []
        for course in req_courses:
            if course in completed_set:
                continue
            # Check if an alternative was completed
            alts = alternatives.get(course, [])
            if any(alt in completed_set for alt in alts):
                continue
            still_needed.append(course)

        if still_needed:
            remaining[cat_key] = still_needed

    return remaining


def check_prereqs_met(course_code: str, completed_codes: set[str], plan: dict) -> bool:
    """Check if all prerequisites for a course are satisfied."""
    prereqs = plan.get("prerequisite_chains", {}).get(course_code, [])
    return all(p in completed_codes for p in prereqs)


def get_available_courses(plan: dict, completed_codes: list[str]) -> list[dict]:
    """
    Get courses that can be taken next — required but not completed,
    with all prerequisites satisfied.

    Returns list of {code, category, label, priority} dicts.
    """
    completed_set = set(completed_codes)
    remaining = get_remaining_courses(plan, completed_codes)
    available = []

    # Priority order: prep → core → electives
    priority_map = {
        "major_introductory": 1,
        "major_prep": 2,
        "major_core": 3,
        "technical_electives": 4,
        "core_curriculum": 5,
        "free_electives": 6,
    }

    for cat_key, courses in remaining.items():
        cat = plan["categories"][cat_key]
        priority = priority_map.get(cat_key, 5)

        for code in courses:
            if check_prereqs_met(code, completed_set, plan):
                available.append({
                    "code": code,
                    "category": cat_key,
                    "label": cat["label"],
                    "priority": priority,
                })

    # Sort by priority (lower = more important)
    available.sort(key=lambda x: x["priority"])
    return available
