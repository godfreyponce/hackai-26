"""
recommender.py — Course recommendation engine with uncertainty modeling.

Scores courses by degree progress, prerequisite readiness, and career
relevance. Applies epistemic and aleatoric uncertainty labels for the
DS/ML hackathon track.
"""

import math
import logging
from typing import Optional

from models.schemas import (
    CompletedCourse,
    CourseRecommendation,
    TranscriptData,
    UncertaintyType,
)
from services.data_loader import get_course_store, CourseInfo
from services.degree_plans import (
    get_degree_plan,
    get_available_courses,
    get_remaining_courses,
    check_prereqs_met,
)

logger = logging.getLogger(__name__)

# ─── Scoring weights ──────────────────────────────────────────────
W_DEGREE_PROGRESS = 0.40   # How much this course advances degree completion
W_PREREQ_DEPTH    = 0.20   # Foundational courses score higher
W_CAREER_MATCH    = 0.20   # Match to student's career goal
W_COURSE_LEVEL    = 0.10   # Prefer courses at the right level for progress
W_CREDITS         = 0.10   # Prefer 3-credit standard courses

# Keywords for career goal matching
CAREER_KEYWORDS = {
    "machine learning": ["machine learning", "artificial intelligence", "data", "neural", "deep learning", "statistics", "probability", "ai", "ml"],
    "software engineering": ["software", "engineering", "systems", "design", "testing", "agile", "devops", "architecture"],
    "cybersecurity": ["security", "crypto", "network", "forensic", "privacy", "malware", "vulnerability"],
    "data science": ["data", "statistics", "analytics", "visualization", "mining", "database", "big data"],
    "web development": ["web", "internet", "network", "database", "full stack", "frontend", "backend"],
    "game development": ["game", "graphics", "animation", "simulation", "rendering", "interactive"],
    "systems": ["operating systems", "compiler", "architecture", "embedded", "hardware", "unix", "linux"],
}


def generate_recommendations(
    transcript: TranscriptData,
    career_goal: Optional[str] = None,
    credits_per_semester: int = 15,
) -> list[CourseRecommendation]:
    """
    Generate scored course recommendations for a student.

    Args:
        transcript: Parsed transcript with completed courses.
        career_goal: Student's career interest (e.g., "machine learning").
        credits_per_semester: Target credit load (default 15).

    Returns:
        Ranked list of CourseRecommendation with confidence and uncertainty.
    """
    store = get_course_store()
    plan = get_degree_plan(transcript.major)

    # Get completed course codes (passing grades only)
    completed_codes = [
        c.course_code for c in transcript.completed_courses
        if c.grade not in ("W", "WL", "WF", "F", "I", "NP", "NF", "NC")
    ]
    # IP (In Progress) courses count as "taken" — don't recommend them again
    in_progress_codes = [
        c.course_code for c in transcript.completed_courses
        if c.grade == "IP"
    ]
    # Combine both so neither completed nor in-progress courses get recommended
    all_taken_codes = completed_codes + in_progress_codes

    # Get courses available to take next (prereqs met, not completed/in-progress)
    available = get_available_courses(plan, all_taken_codes)

    if not available:
        logger.info("No remaining required courses found. Suggesting tech electives.")
        available = _suggest_tech_electives(plan, completed_codes, store)

    # ─── STRICT FLOWCHART ORDER ───────────────────────────────────
    # Only recommend courses from the NEXT semester in the flowchart.
    # If semester 5 has 3 courses, recommend those 3 + fill remaining
    # credits from semester 6 only if needed.
    next_sem_courses = [c for c in available if c.get("semester_distance", 0) == 0]
    fill_courses = [c for c in available if c.get("semester_distance", 0) == 1]

    # If no next-semester courses, fall back to all available
    if not next_sem_courses:
        next_sem_courses = available
        fill_courses = []

    # Score next-semester courses
    recommendations = []
    for item in next_sem_courses:
        code = item["code"]
        course_info = store.get_course(code)

        score, uncertainty = _score_course(
            code=code,
            category=item["category"],
            priority=item["priority"],
            course_info=course_info,
            career_goal=career_goal,
            completed_codes=completed_codes,
            plan=plan,
            store=store,
        )

        title = course_info.title if course_info else code
        reason = _generate_reason(code, item, course_info, career_goal)

        recommendations.append(CourseRecommendation(
            course_code=code,
            course_name=title,
            reason=reason,
            confidence_score=round(score, 3),
            uncertainty_type=uncertainty,
        ))

    # Sort by confidence within the same semester
    recommendations.sort(key=lambda r: r.confidence_score, reverse=True)

    # Check if we need to fill credits from the next semester
    selected = _select_for_semester(recommendations, credits_per_semester, store)
    current_credits = sum(
        (store.get_course(r.course_code).credits if store.get_course(r.course_code) else 3)
        for r in selected
    )

    # Fill remaining credits from next semester if under target
    if current_credits < credits_per_semester and fill_courses:
        fill_recs = []
        for item in fill_courses:
            code = item["code"]
            course_info = store.get_course(code)
            score, uncertainty = _score_course(
                code=code, category=item["category"], priority=item["priority"],
                course_info=course_info, career_goal=career_goal,
                completed_codes=completed_codes, plan=plan, store=store,
            )
            title = course_info.title if course_info else code
            reason = _generate_reason(code, item, course_info, career_goal)
            fill_recs.append(CourseRecommendation(
                course_code=code, course_name=title, reason=reason,
                confidence_score=round(score, 3), uncertainty_type=uncertainty,
            ))
        fill_recs.sort(key=lambda r: r.confidence_score, reverse=True)
        remaining_credits = credits_per_semester - current_credits
        fill_selected = _select_for_semester(fill_recs, int(remaining_credits), store)
        selected.extend(fill_selected)

    return selected


def _score_course(
    code: str,
    category: str,
    priority: int,
    course_info: Optional[CourseInfo],
    career_goal: Optional[str],
    completed_codes: list[str],
    plan: dict,
    store,
) -> tuple[float, Optional[UncertaintyType]]:
    """
    Score a course on [0, 1] and determine uncertainty type.

    Returns (confidence_score, uncertainty_type).
    """
    score = 0.0
    uncertainty = None

    # ── Degree progress score ──
    # Core requirements > electives > free
    priority_scores = {1: 0.7, 2: 0.9, 3: 1.0, 4: 0.6, 5: 0.5, 6: 0.3}
    degree_score = priority_scores.get(priority, 0.5)
    score += W_DEGREE_PROGRESS * degree_score

    # ── Prerequisite depth score ──
    # Courses that unlock many downstream courses score higher
    downstream_count = _count_downstream(code, plan)
    depth_score = min(downstream_count / 5.0, 1.0)  # Normalize to [0, 1]
    score += W_PREREQ_DEPTH * depth_score

    # ── Career match score ──
    career_score = 0.0
    if career_goal and course_info:
        career_score = _career_relevance(course_info, career_goal)
    score += W_CAREER_MATCH * career_score

    # ── Course level appropriateness ──
    if course_info:
        level = int(code.split()[1][0]) if code.split()[1][0].isdigit() else 3
        year_completed = len(completed_codes) / 10  # rough estimate of year
        level_match = 1.0 - abs(level - (year_completed + 1)) * 0.2
        score += W_COURSE_LEVEL * max(0.0, min(1.0, level_match))

    # ── Credits normalization ──
    credits = course_info.credits if course_info else 3
    credit_score = 1.0 if credits == 3 else (0.8 if credits == 4 else 0.6)
    score += W_CREDITS * credit_score

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    # ── Uncertainty classification ──
    uncertainty = _classify_uncertainty(
        code, course_info, career_goal, category, score
    )

    return score, uncertainty


def _classify_uncertainty(
    code: str,
    course_info: Optional[CourseInfo],
    career_goal: Optional[str],
    category: str,
    score: float,
) -> Optional[UncertaintyType]:
    """
    Classify the type of uncertainty in a recommendation.

    Epistemic: We lack data to be confident (fixable with more info).
    Aleatoric: The decision is genuinely ambiguous (irreducible).
    """
    # EPISTEMIC: Missing course info, no description, unknown prerequisites
    if not course_info:
        return UncertaintyType.EPISTEMIC
    if not course_info.description or len(course_info.description) < 20:
        return UncertaintyType.EPISTEMIC

    # ALEATORIC: Technical electives — genuinely multiple good choices
    if category == "technical_electives":
        return UncertaintyType.ALEATORIC

    # ALEATORIC: Mid-range scores suggest genuine tradeoffs
    if 0.4 < score < 0.65:
        return UncertaintyType.ALEATORIC

    # EPISTEMIC: Career goal provided but no clear match to course
    if career_goal and course_info:
        relevance = _career_relevance(course_info, career_goal)
        if relevance < 0.1:
            return UncertaintyType.EPISTEMIC

    return None  # High confidence, no significant uncertainty


def _career_relevance(course_info: CourseInfo, career_goal: str) -> float:
    """Compute career relevance score [0, 1] using keyword matching."""
    goal_lower = career_goal.lower()
    desc_lower = (course_info.description + " " + course_info.title).lower()

    # Find matching career category
    best_match = 0.0
    for career, keywords in CAREER_KEYWORDS.items():
        # Check if career goal matches this category
        if any(kw in goal_lower for kw in keywords[:3]):
            # Count keyword hits in course description
            hits = sum(1 for kw in keywords if kw in desc_lower)
            match = min(hits / max(len(keywords) * 0.4, 1), 1.0)
            best_match = max(best_match, match)

    # Also check direct keyword overlap
    goal_words = set(goal_lower.split())
    desc_words = set(desc_lower.split())
    overlap = len(goal_words & desc_words)
    direct_match = min(overlap / max(len(goal_words), 1), 1.0)

    return max(best_match, direct_match * 0.8)


def _count_downstream(code: str, plan: dict) -> int:
    """Count how many courses in the plan depend on this one."""
    chains = plan.get("prerequisite_chains", {})
    count = 0
    for course, prereqs in chains.items():
        if code in prereqs:
            count += 1
    return count


def _suggest_tech_electives(
    plan: dict,
    completed_codes: list[str],
    store,
) -> list[dict]:
    """Suggest CS 4XXX electives when all required courses are done."""
    completed_set = set(completed_codes)
    suggestions = []

    for code, info in store.courses.items():
        if not code.startswith("CS "):
            continue
        num = code.split()[1]
        if not num.startswith("4"):
            continue
        if code in completed_set:
            continue
        if info.class_level != "Undergraduate":
            continue
        # Check if prereqs are met
        prereqs = store.get_prerequisites(code)
        if all(p in completed_set for p in prereqs):
            suggestions.append({
                "code": code,
                "category": "technical_electives",
                "label": "Technical Electives",
                "priority": 4,
            })

    return suggestions[:20]  # Cap suggestions


def _generate_reason(
    code: str,
    item: dict,
    course_info: Optional[CourseInfo],
    career_goal: Optional[str],
) -> str:
    """Generate a brief reason for recommending this course."""
    parts = []

    # Category context
    cat_reasons = {
        "major_introductory": "Introductory course for your major",
        "major_prep": "Required preparatory course for your degree",
        "major_core": "Core requirement for your CS degree",
        "technical_electives": "Elective that deepens your technical skills",
        "core_curriculum": "Satisfies state core curriculum requirements",
        "free_electives": "Flexible elective to round out your degree",
    }
    parts.append(cat_reasons.get(item["category"], "Part of your degree requirements"))

    # Career relevance
    if career_goal and course_info:
        relevance = _career_relevance(course_info, career_goal)
        if relevance > 0.3:
            parts.append(f"Relevant to your interest in {career_goal}")

    return ". ".join(parts) + "."


def _select_for_semester(
    recommendations: list[CourseRecommendation],
    target_credits: int,
    store,
) -> list[CourseRecommendation]:
    """Select courses that fit within the target credit load."""
    selected = []
    total_credits = 0.0

    for rec in recommendations:
        course_info = store.get_course(rec.course_code)
        credits = course_info.credits if course_info else 3

        if total_credits + credits <= target_credits + 2:  # Allow slight overflow
            selected.append(rec)
            total_credits += credits

        if total_credits >= target_credits:
            break

    return selected
