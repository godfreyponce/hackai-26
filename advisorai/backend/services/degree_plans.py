"""
degree_plans.py — Hardcoded UTD degree plans for CS, CE, SE.

Each plan defines:
- Required courses by category (prep, core, electives, core curriculum)
- Prerequisite chains (what must be taken before what)
- Total hours required

Parsed from the official UTD degree plan PDFs in data/.
"""

from typing import Optional

# ─── Course Difficulty Tiers ─────────────────────────────────────
# Difficulty tier 1 = manageable, 3 = known to be brutal
COURSE_DIFFICULTY = {
    # Tier 1 — straightforward or lighter workload
    "CS 1136": 1, "CS 1337": 1, "CS 2305": 1, "CS 2336": 1,
    "CS 3354": 1, "CS 4141": 1, "CS 1436": 1,
    # Tier 2 — moderate
    "CS 3305": 2, "CS 3341": 2, "CS 4337": 2, "CS 4347": 2,
    "CS 4354": 2, "CS 4361": 2, "CS 4375": 2, "CS 4389": 2,
    "CS 3377": 2, "CS 2340": 2,
    # Tier 3 — difficult / high failure rate
    "CS 3345": 3, "CS 4348": 3, "CS 4349": 3, "CS 4384": 3,
    "CS 4485": 3,
    # Math
    "MATH 2413": 2, "MATH 2414": 2, "MATH 2418": 2, "MATH 2419": 3,
    # Physics
    "PHYS 2325": 2, "PHYS 2326": 2,
}

# GPA thresholds for max difficulty score per semester
GPA_MAX_DIFFICULTY = {
    (3.5, 4.0): 14,   # high achiever — no restrictions
    (3.0, 3.5): 11,   # solid — avoid stacking 3 tier-3 courses
    (2.5, 3.0): 9,    # average — max 1 tier-3 per semester
    (0.0, 2.5): 7,    # struggling — protect from overloading
}

TOTAL_DEGREE_HOURS = 124


def get_semester_difficulty_score(course_codes: list[str]) -> int:
    """Sum of difficulty tiers for all courses in a semester."""
    return sum(COURSE_DIFFICULTY.get(c, 2) for c in course_codes)


def get_max_difficulty_for_gpa(gpa: float) -> int:
    """Get the maximum semester difficulty score for a given GPA."""
    for (low, high), max_diff in GPA_MAX_DIFFICULTY.items():
        if low <= gpa <= high:
            return max_diff
    return 9  # safe default


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
            "label": "Technical Electives (pick 4)",
            "hours": 12,
            "courses": [
                "CS 4314",    # Intelligent Systems Analysis
                "CS 4337",    # Organization of Programming Languages (also core, listed as option)
                "CS 4352",    # Human-Computer Interaction
                "CS 4361",    # Computer Graphics
                "CS 4365",    # Artificial Intelligence
                "CS 4375",    # Introduction to Machine Learning
                "CS 4386",    # Compiler Design
                "CS 4389",    # Data and Applications Security
                "CS 4390",    # Computer Networks
                "CS 4391",    # Introduction to Computer Vision
                "CS 4393",    # Computer and Network Security
                "CS 4395",    # Human Language Technologies
                "CS 4396",    # Networking Laboratory
                "CS 4397",    # Embedded Computer Systems
                "CS 4398",    # Digital Forensics
                "CS 4399",    # Cloud Computing
            ],
            "pick": 4,  # Student picks 4 of these
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
        # ─── Verified against official CS Flowchart 2025-2026 ───
        # Math chain
        "MATH 2414": ["MATH 2413"],       # Calc II requires Calc I
        "MATH 2419": ["MATH 2417"],       # Calc II alt requires Calc I alt
        "MATH 2418": ["MATH 2413"],       # Linear Algebra requires Calc I (NOT Calc II)
        # Physics chain
        "PHYS 2325": ["MATH 2413"],       # Mechanics requires Calc I (coreq: MATH 2414)
        "PHYS 2125": ["PHYS 2325"],       # Physics Lab I
        "PHYS 2326": ["PHYS 2325", "MATH 2414"],  # E&M requires Mechanics + Calc II
        "PHYS 2126": ["PHYS 2326"],       # Physics Lab II
        # CS chain — Semester 1-2
        "CS 1337": ["CS 1436"],           # CS I requires Programming Fundamentals
        "CS 2305": ["MATH 2413"],         # Discrete Math requires Calc I (NOT CS 1337)
        # CS chain — Semester 3
        "CS 2336": ["CS 1337"],           # CS II (Java) requires CS I
        "CS 2337": ["CS 1337"],           # CS II (C++) requires CS I
        "CS 2340": ["CS 1337", "CS 2305"],  # Architecture requires CS I + Discrete Math
        # CS chain — Semester 4
        "ECS 2390": ["RHET 1302"],        # Tech Comm requires RHET (NOT CS 2336)
        "CS 3341": ["MATH 2414", "CS 2305", "MATH 2418"],  # Stats requires Calc II + Discrete + LinAlg
        "CS 3345": ["CS 2336", "CS 2305"],  # Data Structures requires CS II + Discrete
        "CS 3377": ["CS 2336"],           # Systems Programming requires CS II
        # CS chain — Semester 5
        "CS 4337": ["CS 2336", "CS 2305", "CS 2340"],  # PL Paradigms requires CS II + Discrete + Architecture
        "CS 4341": ["PHYS 2326", "CS 2340"],  # Digital Logic requires E&M + Architecture
        "CS 4141": ["CS 4341"],           # Digital Systems Lab requires Digital Logic
        "CS 3354": ["CS 2336", "CS 2305", "ECS 2390"],  # Software Eng requires CS II + Discrete + Tech Comm (NOT CS 3345)
        # CS chain — Semester 6
        "CS 4349": ["CS 2305", "CS 3345"],  # Adv Algorithms requires Discrete + Data Structures
        "CS 3162": ["ECS 2390", "GOVT 2305"],  # Prof Responsibility requires Tech Comm + Govt (NOT CS 3345)
        "CS 4348": ["CS 2340", "CS 3377", "CS 3345"],  # OS requires Architecture + SysProg + DS
        # CS chain — Semester 7
        "CS 4384": ["CS 2305"],           # Automata Theory requires Discrete Math (NOT CS 3345)
        "CS 4347": ["CS 3345"],           # Database Systems requires Data Structures
        # CS chain — Semester 8
        "CS 4485": ["CS 3345", "CS 3354"],  # CS Project requires DS + SWE (+ 3 tech electives)
    },
    # Corequisites (can be taken at the same time)
    "corequisites": {
        "PHYS 2325": ["MATH 2414"],       # Mechanics can be taken WITH Calc II
    },
    # Critical path courses (must not be delayed)
    "critical_path": [
        "MATH 2413", "CS 1337", "CS 2305", "CS 2336", "CS 3345", "CS 4348",
    ],
    # Semester sequence from official UTD CS Flowchart 2025-2026
    "semester_sequence": {
        # Semester 1 (Fall Year 1)
        "CS 1436": 1, "MATH 2413": 1, "MATH 2417": 1,
        "ECS 1100": 1, "CS 1200": 1,
        # Semester 2 (Spring Year 1)
        "CS 1337": 2, "MATH 2414": 2, "MATH 2419": 2,
        "PHYS 2325": 2, "PHYS 2125": 2, "CS 2305": 2,
        # Semester 3 (Fall Year 2)
        "CS 2336": 3, "CS 2337": 3, "CS 2340": 3,
        "PHYS 2326": 3, "PHYS 2126": 3, "MATH 2418": 3,
        # Semester 4 (Spring Year 2)
        "ECS 2390": 4, "CS 3341": 4, "CS 3345": 4, "CS 3377": 4,
        # Semester 5 (Fall Year 3)
        "CS 4337": 5, "CS 4341": 5, "CS 4141": 5, "CS 3354": 5,
        # Semester 6 (Spring Year 3)
        "CS 4349": 6, "CS 3162": 6, "CS 4348": 6,
        # Semester 7 (Fall Year 4)
        "CS 4384": 7, "CS 4347": 7,
        # Semester 8 (Spring Year 4)
        "CS 4485": 8,
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


# ─── Minor Plans ─────────────────────────────────────────────────

FINANCE_MINOR = {
    "name": "Finance",
    "type": "minor",
    "total_hours": 18,
    "subject_prefixes": ["FIN", "ACCT"],
    "required_courses": [
        "ACCT 2301",  # Introductory Financial Accounting
        "ACCT 2302",  # Managerial Accounting
        "FIN 3320",   # Business Finance
        "FIN 3330",   # Financial Statement Analysis
        "FIN 3390",   # Corporate Finance
        "FIN 4320",   # Investments
    ],
    "prerequisite_chains": {
        "ACCT 2302": ["ACCT 2301"],
        "FIN 3320": ["ACCT 2301"],
        "FIN 3330": ["ACCT 2301", "FIN 3320"],
        "FIN 3390": ["FIN 3320"],
        "FIN 4320": ["FIN 3320"],
    },
    "notes": "Naveen Jindal School of Management. CS students may need advisor approval.",
}

BUSINESS_MINOR = {
    "name": "Business",
    "type": "minor",
    "total_hours": 18,
    "subject_prefixes": ["BA", "MKT", "FIN", "OPRE", "ACCT"],
    "required_courses": [
        "ACCT 2301",  # Introductory Financial Accounting
        "BA 3301",    # Business Law
        "BA 3341",    # Organizational Behavior
        "MKT 3300",   # Principles of Marketing
        "FIN 3100",   # Personal Finance
        "OPRE 3310",  # Introduction to Operations Research
    ],
    "prerequisite_chains": {},
    "notes": "Jindal School of Management minor.",
}

MATH_MINOR = {
    "name": "Mathematics",
    "type": "minor",
    "total_hours": 18,
    "subject_prefixes": ["MATH"],
    "required_courses": [
        "MATH 2413",  # Calculus I (or equivalent)
        "MATH 2414",  # Calculus II
        "MATH 2418",  # Linear Algebra
        "MATH 3310",  # Theoretical Concepts of Calculus
        "MATH 3311",  # Abstract Algebra I
        "MATH 4334",  # Numerical Analysis
    ],
    "prerequisite_chains": {
        "MATH 2414": ["MATH 2413"],
        "MATH 2418": ["MATH 2413"],
        "MATH 3310": ["MATH 2414"],
        "MATH 3311": ["MATH 2414"],
        "MATH 4334": ["MATH 3311"],
    },
    "notes": "Department of Mathematical Sciences.",
}

DATA_SCIENCE_MINOR = {
    "name": "Data Science",
    "type": "minor",
    "total_hours": 15,
    "subject_prefixes": ["STAT", "CS"],
    "required_courses": [
        "CS 3341",    # Probability and Statistics — can count for major too
        "STAT 3355",  # Statistics for Life Sciences (alt: STAT 4382)
        "CS 4375",    # Machine Learning
        "STAT 4382",  # Applied Statistics
        "CS 4395",    # Human Language Technologies (or other data-intensive CS elective)
    ],
    "prerequisite_chains": {
        "CS 3341": ["MATH 2414", "CS 2305"],
        "STAT 3355": ["MATH 2414"],
        "CS 4375": ["CS 3354"],
        "STAT 4382": ["STAT 3355"],
    },
    "notes": "Unofficial — verify current requirements at utdallas.edu",
}

PSYCHOLOGY_MINOR = {
    "name": "Psychology",
    "type": "minor",
    "total_hours": 18,
    "subject_prefixes": ["PSY"],
    "required_courses": [
        "PSY 2301",  # Introduction to Psychology
        "PSY 2314",  # Lifespan Development
        "PSY 3331",  # Abnormal Psychology
        "PSY 3380",  # Cognitive Psychology
        "PSY 4329",  # Research Methods in Psychology
        "PSY 4342",  # Psychology Elective (upper div)
    ],
    "prerequisite_chains": {
        "PSY 3331": ["PSY 2301"],
        "PSY 3380": ["PSY 2301"],
        "PSY 4329": ["PSY 2301"],
        "PSY 4342": ["PSY 2301"],
    },
    "notes": "School of Behavioral and Brain Sciences.",
}

ECONOMICS_MINOR = {
    "name": "Economics",
    "type": "minor",
    "total_hours": 18,
    "subject_prefixes": ["ECON"],
    "required_courses": [
        "ECON 2301",  # Principles of Macroeconomics
        "ECON 2302",  # Principles of Microeconomics
        "ECON 3310",  # Intermediate Microeconomics
        "ECON 3311",  # Intermediate Macroeconomics
        "ECON 4320",  # Econometrics
        "ECON 4350",  # Economics Elective (upper div)
    ],
    "prerequisite_chains": {
        "ECON 3310": ["ECON 2302"],
        "ECON 3311": ["ECON 2301"],
        "ECON 4320": ["ECON 3310", "ECON 3311"],
        "ECON 4350": ["ECON 3310"],
    },
    "notes": "School of Economic, Political and Policy Sciences.",
}

NEUROSCIENCE_MINOR = {
    "name": "Neuroscience",
    "type": "minor",
    "total_hours": 19,
    "subject_prefixes": ["COGS", "PSY", "BIOL"],
    "required_courses": [
        "COGS 2301",  # Intro to Cognitive Science
        "PSY 2301",   # Intro to Psychology
        "BIOL 2311",  # Intro to Modern Biology
        "COGS 3301",  # Foundations of Cognitive Science
        "COGS 4310",  # Computational Neuroscience
        "PSY 3380",   # Cognitive Psychology
    ],
    "prerequisite_chains": {
        "COGS 3301": ["COGS 2301"],
        "COGS 4310": ["COGS 3301"],
        "PSY 3380": ["PSY 2301"],
    },
    "notes": "School of Behavioral and Brain Sciences.",
}

MINOR_PLANS: dict[str, dict] = {
    # Primary keys (normalized lowercase)
    "finance": FINANCE_MINOR,
    "business": BUSINESS_MINOR,
    "mathematics": MATH_MINOR,
    "math": MATH_MINOR,
    "data science": DATA_SCIENCE_MINOR,
    "data_science": DATA_SCIENCE_MINOR,
    "datascience": DATA_SCIENCE_MINOR,
    "psychology": PSYCHOLOGY_MINOR,
    "psych": PSYCHOLOGY_MINOR,
    "economics": ECONOMICS_MINOR,
    "econ": ECONOMICS_MINOR,
    "neuroscience": NEUROSCIENCE_MINOR,
    "neuro": NEUROSCIENCE_MINOR,
}


def get_minor_plan(minor_name: str) -> dict | None:
    """
    Look up a minor plan by name. Case-insensitive, handles common abbreviations.
    Returns None for unknown minors — caller should fall back to LLM judgment.
    """
    if not minor_name:
        return None
    normalized = minor_name.lower().strip()
    # Exact match first
    if normalized in MINOR_PLANS:
        return MINOR_PLANS[normalized]
    # Partial match
    for key, plan in MINOR_PLANS.items():
        if normalized in key or key in normalized:
            return plan
    return None


def get_minor_subject_prefixes(minor_name: str) -> list[str]:
    """Get the Nebula subject prefixes to search for a given minor."""
    plan = get_minor_plan(minor_name)
    if plan:
        return plan.get("subject_prefixes", [])
    # For unknown minors, guess from the name
    common_prefixes = {
        "accounting": ["ACCT"],
        "communications": ["COMM"],
        "history": ["HIST"],
        "philosophy": ["PHIL"],
        "sociology": ["SOC"],
        "political": ["GOVT"],
        "arts": ["ATCM", "ARTS"],
    }
    lower = minor_name.lower()
    for keyword, prefixes in common_prefixes.items():
        if keyword in lower:
            return prefixes
    return []


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
    For elective categories with 'pick' count, only include enough to fill the requirement.
    """
    completed_set = set(completed_codes)
    remaining = {}

    for cat_key, cat in plan["categories"].items():
        req_courses = cat.get("courses", [])
        alternatives = cat.get("alternatives", {})
        pick_count = cat.get("pick")  # e.g. "pick 4 of these"

        still_needed = []
        completed_in_cat = 0
        for course in req_courses:
            if course in completed_set:
                completed_in_cat += 1
                continue
            # Check if an alternative was completed
            alts = alternatives.get(course, [])
            if any(alt in completed_set for alt in alts):
                completed_in_cat += 1
                continue
            still_needed.append(course)

        # For "pick N" categories (electives), only include enough to fill requirement
        if pick_count is not None:
            slots_remaining = max(0, pick_count - completed_in_cat)
            still_needed = still_needed[:slots_remaining]

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

    Uses semester_sequence from the flowchart to prioritize courses
    from the student's NEXT semester rather than jumping ahead.

    Returns list of {code, category, label, priority, target_semester} dicts.
    """
    completed_set = set(completed_codes)
    remaining = get_remaining_courses(plan, completed_codes)
    semester_seq = plan.get("semester_sequence", {})

    # Determine student's current semester based on completed courses
    current_semester = _detect_current_semester(completed_set, semester_seq)

    available = []

    # Priority order: prep → core → electives
    category_priority = {
        "major_introductory": 1,
        "major_prep": 2,
        "major_core": 3,
        "technical_electives": 4,
        "core_curriculum": 5,
        "free_electives": 6,
    }

    for cat_key, courses in remaining.items():
        cat = plan["categories"][cat_key]
        cat_pri = category_priority.get(cat_key, 5)

        for code in courses:
            if check_prereqs_met(code, completed_set, plan):
                target_sem = semester_seq.get(code, 99)
                # Semester distance from current (courses in next semester = 0, two ahead = 1, etc.)
                sem_distance = max(0, target_sem - current_semester)

                available.append({
                    "code": code,
                    "category": cat_key,
                    "label": cat["label"],
                    "priority": cat_pri,
                    "target_semester": target_sem,
                    "semester_distance": sem_distance,
                })

    # Sort by: semester distance first (next semester first), then category priority
    available.sort(key=lambda x: (x["semester_distance"], x["priority"]))
    return available


def _detect_current_semester(completed_codes: set[str], semester_seq: dict) -> int:
    """
    Detect what semester the student is currently in based on completed courses.
    Returns the next semester they should take (the one they haven't completed yet).
    """
    if not semester_seq:
        return 1

    # Group courses by semester
    semesters: dict[int, list[str]] = {}
    for code, sem in semester_seq.items():
        semesters.setdefault(sem, []).append(code)

    # Find the first semester where more than half the courses are NOT completed
    for sem_num in sorted(semesters.keys()):
        sem_courses = semesters[sem_num]
        completed_count = sum(1 for c in sem_courses if c in completed_codes)
        # If less than half completed, this is the current semester
        if completed_count < len(sem_courses) / 2:
            return sem_num

    # All semesters mostly complete — they're at the end
    return max(semesters.keys()) + 1


# ─── Course Difficulty Tiers ──────────────────────────────────────
# Tier 1 = manageable, 2 = moderate, 3 = known to be brutal
COURSE_DIFFICULTY: dict[str, int] = {
    # Tier 1 — lighter workload
    "CS 1436": 1, "CS 1200": 1, "ECS 1100": 1,
    "CS 1337": 1, "CS 2305": 1, "CS 2336": 1, "CS 2337": 1,
    "CS 3354": 1, "CS 4141": 1, "CS 3162": 1, "ECS 2390": 1,
    # Tier 2 — moderate
    "CS 2340": 2, "CS 3305": 2, "CS 3341": 2, "CS 3377": 2,
    "CS 4337": 2, "CS 4341": 2, "CS 4347": 2,
    "CS 4354": 2, "CS 4361": 2, "CS 4375": 2, "CS 4389": 2,
    "MATH 2413": 2, "MATH 2414": 2, "MATH 2418": 2,
    "PHYS 2325": 2, "PHYS 2326": 2,
    # Tier 3 — difficult / high failure rate
    "CS 3345": 3, "CS 4348": 3, "CS 4349": 3, "CS 4384": 3,
    "CS 4485": 3, "MATH 2419": 3,
}

# GPA thresholds for max difficulty score per semester
GPA_MAX_DIFFICULTY: dict[tuple[float, float], int] = {
    (3.5, 4.0): 14,   # high achiever — no restrictions
    (3.0, 3.5): 11,   # solid — avoid stacking 3 tier-3 courses
    (2.5, 3.0): 9,    # average — max 1 tier-3 per semester
    (0.0, 2.5): 7,    # struggling — protect from overloading
}


def get_semester_difficulty_score(course_codes: list[str]) -> int:
    """Sum of difficulty tiers for all courses in a semester."""
    return sum(COURSE_DIFFICULTY.get(c, 2) for c in course_codes)


def get_max_difficulty_for_gpa(gpa: float) -> int:
    for (low, high), max_diff in GPA_MAX_DIFFICULTY.items():
        if low <= gpa <= high:
            return max_diff
    return 9  # safe default


def get_fallback_courses() -> list[dict]:
    """
    Return a minimal hardcoded list of CS courses as JSON-serializable dicts.
    Used when the Nebula API is unavailable and no local cache exists.
    """
    courses = []
    for plan in [CS_DEGREE_PLAN, CE_DEGREE_PLAN, SE_DEGREE_PLAN]:
        prereqs = plan.get("prerequisite_chains", {})
        for cat in plan["categories"].values():
            for code in cat.get("courses", []):
                subject, *rest = code.split()
                number = rest[0] if rest else ""
                courses.append({
                    "_id": code.replace(" ", ""),
                    "subject_prefix": subject,
                    "course_number": number,
                    "title": code,
                    "description": f"{cat.get('label', '')} requirement",
                    "credit_hours": "3",
                    "prerequisites": None,
                    "_prereq_codes": prereqs.get(code, []),
                })
    # Deduplicate by course id
    seen: set[str] = set()
    unique = []
    for c in courses:
        key = f"{c['subject_prefix']} {c['course_number']}"
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique
