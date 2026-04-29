"""Seed the database with a baseline of users, exercises, plan templates,
weekly split templates, and a small mix of live assignments.

Idempotent via natural keys (email for users, name for exercises, title for
plan templates, label for weekly templates, and a per-user check on
``assignments`` for the live assignment seed). All primary keys are
auto-generated UUIDs — the seed never hardcodes IDs. Safe to re-run after
migrations.

Run from the backend/ directory:

    python -m scripts.seed
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlmodel import Session, select

from db import engine
from models import (
    Exercise,
    Plan,
    PlanTemplate,
    User,
    UserPlanAssignment,
    UserPlanAssignmentStatus,
    WeeklySplitTemplate,
)
from services.auth import hash_password
from services.template_service import instantiate_plan_template

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")


# --- Users -----------------------------------------------------------------

# Default password for every seeded user. Real signups go through
# /api/auth/signup and pick their own; this is just so you can `Sign in` as
# the seed admin without going through signup first.
SEED_PASSWORD = "ChangeMe!23"

# Mixed shape — some users have gender / phone set, some don't, so the UI
# (UserDetailsDialog "Profile" row, UsersList table) shows both populated
# and "—" cases.
USERS: list[dict] = [
    # Admin-only seed user. Intentionally has no plan assignment so the
    # e2e suite can sign in and act on every other user without being a
    # subject of those actions themselves. Distinct from Tahseen (who is
    # mid-plan and exercises the in-progress assignment paths).
    {
        "first_name": "Fake",
        "last_name": "Admin",
        "email": "fakeadmin@example.com",
        "timezone": "Europe/Amsterdam",
    },
    {
        "first_name": "Tahseen",
        "last_name": "Shamsi",
        "email": "tahseen@example.com",
        "timezone": "Europe/Amsterdam",
        "gender": "male",
        "phone_number": "+31 6 1234 5678",
    },
    {
        "first_name": "Alex",
        "last_name": "Rodriguez",
        "email": "alex.r@example.com",
        "timezone": "America/New_York",
        "gender": "male",
        "phone_number": "+1 212 555 0143",
    },
    {
        "first_name": "Maya",
        "last_name": "Patel",
        "email": "maya.patel@example.com",
        "timezone": "Asia/Kolkata",
        "gender": "female",
        "phone_number": "+91 98765 43210",
    },
    {
        "first_name": "Jordan",
        "last_name": "Kim",
        "email": "jordan.kim@example.com",
        "timezone": "Asia/Tokyo",
        "gender": "other",
        # phone deliberately omitted to exercise the "—" placeholder.
    },
    {
        "first_name": "Sam",
        "last_name": "Carter",
        "email": "sam.carter@example.com",
        "timezone": "America/Los_Angeles",
        # gender + phone omitted.
    },
    {
        "first_name": "Lily",
        "last_name": "Chen",
        "email": "lily.chen@example.com",
        "timezone": "Australia/Sydney",
        "gender": "female",
        "phone_number": "+61 412 345 678",
    },
]


# --- Exercises -------------------------------------------------------------

EXERCISES: list[dict] = [
    {"name": "Bench Press",            "body_category": "chest",     "equipment": "bar",         "usage_count": 1842},
    {"name": "Back Squat",             "body_category": "legs",      "equipment": "bar",         "usage_count": 1620},
    {"name": "Deadlift",               "body_category": "back",      "equipment": "bar",         "usage_count": 1455},
    {"name": "Overhead Press",         "body_category": "shoulders", "equipment": "bar",         "usage_count": 870},
    {"name": "Pull-Up",                "body_category": "back",      "equipment": "free-weight", "usage_count": 1180},
    {"name": "Plank",                  "body_category": "core",      "equipment": "free-weight", "usage_count": 980},
    {"name": "Incline Dumbbell Press", "body_category": "chest",     "equipment": "dumbbell",    "usage_count": 180},
    {"name": "Romanian Deadlift",      "body_category": "legs",      "equipment": "bar",         "usage_count": 645},
    {"name": "Leg Press",              "body_category": "legs",      "equipment": "machine",     "usage_count": 295},
    {"name": "Lateral Raise",          "body_category": "shoulders", "equipment": "dumbbell",    "usage_count": 470},
    {"name": "Bicep Curl",             "body_category": "arms",      "equipment": "dumbbell",    "usage_count": 760},
    {"name": "Tricep Dip",             "body_category": "arms",      "equipment": "free-weight", "usage_count": 580},
    {"name": "Barbell Row",            "body_category": "back",      "equipment": "bar",         "usage_count": 510},
    {"name": "Lat Pulldown",           "body_category": "back",      "equipment": "cable",       "usage_count": 390},
    {"name": "Russian Twist",          "body_category": "core",      "equipment": "free-weight", "usage_count": 320},
    {"name": "Burpee",                 "body_category": "cardio",    "equipment": "free-weight", "usage_count": 350},
    {"name": "Mountain Climber",       "body_category": "cardio",    "equipment": "free-weight", "usage_count": 220},
    {"name": "Lunges",                 "body_category": "legs",      "equipment": "free-weight", "usage_count": 430},
    {"name": "Push-Up",                "body_category": "chest",     "equipment": "free-weight", "usage_count": 1090},
    {"name": "Hammer Curl",            "body_category": "arms",      "equipment": "dumbbell",    "usage_count": 250},
    {"name": "Face Pull",              "body_category": "shoulders", "equipment": "cable",       "usage_count": 210},
    {"name": "Goblet Squat",           "body_category": "legs",      "equipment": "dumbbell",    "usage_count": 410},
    {"name": "Hip Thrust",             "body_category": "legs",      "equipment": "bar",         "usage_count": 540},
    {"name": "Calf Raise",             "body_category": "legs",      "equipment": "machine",     "usage_count": 280},
    {"name": "Cable Fly",              "body_category": "chest",     "equipment": "cable",       "usage_count": 200},
]


# --- Helpers ---------------------------------------------------------------


def at_local_noon(d: date) -> datetime:
    """Anchor an ``assigned_at`` timestamp to noon UTC on ``d`` so the seeded
    history orders deterministically by date (and a slightly later same-day
    re-creation can still beat it via a real ``utcnow``)."""
    return datetime.combine(d, time(hour=12, minute=0, tzinfo=timezone.utc))


def seed_users(session: Session) -> None:
    """Insert seed users with a known password so `Sign in` works locally.

    Idempotent — re-running won't reset passwords or rewrite gender / phone
    for existing rows. To reset a seeded user, drop the row first.
    """
    inserted = 0
    pw_hash = hash_password(SEED_PASSWORD)
    for row in USERS:
        existing = session.exec(select(User).where(User.email == row["email"])).first()
        if existing is not None:
            continue
        session.add(User(**row, password_hash=pw_hash))
        inserted += 1
    log.info(
        "users: %d new (of %d) — password for all seed users: %s",
        inserted,
        len(USERS),
        SEED_PASSWORD if inserted else "(unchanged)",
    )


def seed_exercises(session: Session) -> None:
    inserted = 0
    for row in EXERCISES:
        existing = session.exec(select(Exercise).where(Exercise.name == row["name"])).first()
        if existing is not None:
            continue
        session.add(Exercise(**row))
        inserted += 1
    log.info("exercises: %d new (of %d)", inserted, len(EXERCISES))


# --- Templates -------------------------------------------------------------

STRENGTH_BLOCK_LABEL = "Strength Block"
ENDURANCE_BLOCK_LABEL = "Endurance Block"

STARTER_PLAN_TITLE = "Full-Body Strength Starter"
RUNNER_PLAN_TITLE = "5K Runner Prep"


def strength_block_days(exercises_by_name: dict[str, str]) -> list[dict]:
    """Seven-day push/pull/legs split with two off-days, used by both the
    standalone ``WeeklySplitTemplate`` and inline inside the strength
    ``PlanTemplate``."""

    def exercise(name: str, sets: int, reps: int, order: int) -> dict:
        return {
            "exerciseId": exercises_by_name.get(name),
            "exerciseName": name,
            "sets": sets,
            "reps": reps,
            "weight": None,
            "weightUnit": "kg",
            "restSeconds": 90,
            "orderIndex": order,
        }

    days_spec = [
        ("Day 1 — Push", False, [("Bench Press", 4, 8), ("Overhead Press", 4, 8), ("Push-Up", 3, 15)]),
        ("Day 2 — Rest", True, []),
        ("Day 3 — Pull", False, [("Deadlift", 3, 6), ("Barbell Row", 4, 8), ("Pull-Up", 3, 10)]),
        ("Day 4 — Rest", True, []),
        ("Day 5 — Legs", False, [("Back Squat", 5, 5), ("Romanian Deadlift", 4, 8), ("Lunges", 3, 12)]),
        ("Day 6 — Rest", True, []),
        ("Day 7 — Rest", True, []),
    ]
    days: list[dict] = []
    for idx, (label, is_rest, exes) in enumerate(days_spec):
        days.append(
            {
                "label": label,
                "isRest": is_rest,
                "orderIndex": idx,
                "exercises": [
                    exercise(name, sets, reps, ei)
                    for ei, (name, sets, reps) in enumerate(exes)
                ],
            }
        )
    return days


def endurance_block_days(exercises_by_name: dict[str, str]) -> list[dict]:
    """Seven-day endurance / conditioning split. Three workout days
    (cardio + bodyweight + core) plus four rest/recovery days."""

    def exercise(name: str, sets: int, reps: int, order: int) -> dict:
        return {
            "exerciseId": exercises_by_name.get(name),
            "exerciseName": name,
            "sets": sets,
            "reps": reps,
            "weight": None,
            "weightUnit": "kg",
            "restSeconds": 60,
            "orderIndex": order,
        }

    days_spec = [
        ("Day 1 — Conditioning", False, [("Burpee", 3, 15), ("Mountain Climber", 3, 30), ("Plank", 3, 1)]),
        ("Day 2 — Recovery", True, []),
        ("Day 3 — Lower body", False, [("Goblet Squat", 3, 12), ("Lunges", 3, 12), ("Calf Raise", 3, 15)]),
        ("Day 4 — Recovery", True, []),
        ("Day 5 — Upper body", False, [("Push-Up", 3, 15), ("Lat Pulldown", 3, 12), ("Face Pull", 3, 15)]),
        ("Day 6 — Recovery", True, []),
        ("Day 7 — Recovery", True, []),
    ]
    days: list[dict] = []
    for idx, (label, is_rest, exes) in enumerate(days_spec):
        days.append(
            {
                "label": label,
                "isRest": is_rest,
                "orderIndex": idx,
                "exercises": [
                    exercise(name, sets, reps, ei)
                    for ei, (name, sets, reps) in enumerate(exes)
                ],
            }
        )
    return days


def seed_templates(session: Session) -> None:
    """Two ``WeeklySplitTemplate`` rows + two ``PlanTemplate`` rows.

    Idempotent on label / title — pre-existing rows are left alone, even if
    their structure has been edited by an admin.
    """
    exercises_by_name: dict[str, str] = {
        ex.name: ex.id for ex in session.exec(select(Exercise)).all()
    }

    strength_days = strength_block_days(exercises_by_name)
    endurance_days = endurance_block_days(exercises_by_name)

    # --- WeeklySplitTemplates -----------------------------------------------
    weekly_strength = session.exec(
        select(WeeklySplitTemplate).where(
            WeeklySplitTemplate.label == STRENGTH_BLOCK_LABEL
        )
    ).first()
    if weekly_strength is None:
        weekly_strength = WeeklySplitTemplate(
            label=STRENGTH_BLOCK_LABEL, days=strength_days
        )
        session.add(weekly_strength)
        session.flush()
        log.info("weekly split template '%s': created", STRENGTH_BLOCK_LABEL)
    else:
        log.info(
            "weekly split template '%s': already present", STRENGTH_BLOCK_LABEL
        )

    weekly_endurance = session.exec(
        select(WeeklySplitTemplate).where(
            WeeklySplitTemplate.label == ENDURANCE_BLOCK_LABEL
        )
    ).first()
    if weekly_endurance is None:
        weekly_endurance = WeeklySplitTemplate(
            label=ENDURANCE_BLOCK_LABEL, days=endurance_days
        )
        session.add(weekly_endurance)
        session.flush()
        log.info("weekly split template '%s': created", ENDURANCE_BLOCK_LABEL)
    else:
        log.info(
            "weekly split template '%s': already present", ENDURANCE_BLOCK_LABEL
        )

    # --- PlanTemplates ------------------------------------------------------
    starter = session.exec(
        select(PlanTemplate).where(PlanTemplate.title == STARTER_PLAN_TITLE)
    ).first()
    if starter is None:
        starter = PlanTemplate(
            title=STARTER_PLAN_TITLE,
            duration=8,
            duration_type="weeks",
            workout_days_per_week=3,
            weekly_plans=[
                {
                    "weeklySplitTemplateId": weekly_strength.id,
                    "label": weekly_strength.label,
                    "days": strength_days,
                    "weekFrequency": 8,
                    "orderIndex": 0,
                }
            ],
            flat_days=None,
        )
        session.add(starter)
        session.flush()
        log.info("plan template '%s': created", STARTER_PLAN_TITLE)
    else:
        log.info("plan template '%s': already present", STARTER_PLAN_TITLE)

    runner = session.exec(
        select(PlanTemplate).where(PlanTemplate.title == RUNNER_PLAN_TITLE)
    ).first()
    if runner is None:
        runner = PlanTemplate(
            title=RUNNER_PLAN_TITLE,
            duration=4,
            duration_type="weeks",
            workout_days_per_week=3,
            weekly_plans=[
                {
                    "weeklySplitTemplateId": weekly_endurance.id,
                    "label": weekly_endurance.label,
                    "days": endurance_days,
                    "weekFrequency": 4,
                    "orderIndex": 0,
                }
            ],
            flat_days=None,
        )
        session.add(runner)
        session.flush()
        log.info("plan template '%s': created", RUNNER_PLAN_TITLE)
    else:
        log.info("plan template '%s': already present", RUNNER_PLAN_TITLE)


# --- Live assignments ------------------------------------------------------

# (user email, plan title, status, days_offset_from_today_for_start)
# days_offset is negative for past starts. end_date is computed from the
# plan's duration in days. assigned_at is anchored to the start_date so
# the History sort orders deterministically.
ASSIGNMENT_SEEDS: list[tuple[str, str, UserPlanAssignmentStatus, int]] = [
    # Seed admin: currently mid-plan on the strength starter.
    (
        "tahseen@example.com",
        STARTER_PLAN_TITLE,
        UserPlanAssignmentStatus.in_progress,
        -14,
    ),
    # Alex: completed the runner block last month — shows up under History.
    (
        "alex.r@example.com",
        RUNNER_PLAN_TITLE,
        UserPlanAssignmentStatus.completed,
        -60,
    ),
    # Alex: now on the strength starter, in-progress.
    (
        "alex.r@example.com",
        STARTER_PLAN_TITLE,
        UserPlanAssignmentStatus.in_progress,
        -7,
    ),
    # Maya: started the strength starter but cancelled mid-plan.
    (
        "maya.patel@example.com",
        STARTER_PLAN_TITLE,
        UserPlanAssignmentStatus.cancelled,
        -30,
    ),
    # Jordan: paused on the runner block.
    (
        "jordan.kim@example.com",
        RUNNER_PLAN_TITLE,
        UserPlanAssignmentStatus.paused,
        -10,
    ),
]


def plan_total_days_from_template(template: PlanTemplate) -> int:
    duration_type = (
        template.duration_type.value
        if hasattr(template.duration_type, "value")
        else template.duration_type
    )
    multiplier = {"days": 1, "weeks": 7, "months": 30, "years": 365}.get(
        duration_type, 1
    )
    return template.duration * multiplier


def seed_assignments(session: Session) -> None:
    """Materialise a small mix of live ``Plan`` rows + ``UserPlanAssignment``
    rows so the dashboard's Active Plans list has multiple plans to render
    and at least one user has multi-row plan history.

    Idempotent against the user — if a user already has any assignment
    we skip them entirely (don't try to merge against existing data).
    """
    today = date.today()

    by_email: dict[str, User] = {
        u.email: u for u in session.exec(select(User)).all()
    }
    by_title: dict[str, PlanTemplate] = {
        t.title: t for t in session.exec(select(PlanTemplate)).all()
    }

    # Group seeds by user so we can skip a user wholesale if they already
    # have any assignment row in the DB. Avoids creating duplicate plans
    # on re-seed.
    grouped: dict[str, list[tuple[str, UserPlanAssignmentStatus, int]]] = {}
    for email, title, status, offset in ASSIGNMENT_SEEDS:
        grouped.setdefault(email, []).append((title, status, offset))

    inserted_users = 0
    for email, rows in grouped.items():
        user = by_email.get(email)
        if user is None:
            log.warning("assignment seed: user %s not found, skipping", email)
            continue
        if user.assignments:
            log.info("assignment seed for %s: already present, skipping", email)
            continue

        for title, status, offset in rows:
            template = by_title.get(title)
            if template is None:
                log.warning(
                    "assignment seed: plan template %r missing for %s, skipping",
                    title,
                    email,
                )
                continue

            plan = instantiate_plan_template(session, template)
            session.add(plan)
            session.flush()

            start = today + timedelta(days=offset)
            duration_days = plan_total_days_from_template(template)
            end = start + timedelta(days=duration_days)

            remaining: int | None = None
            if status == UserPlanAssignmentStatus.paused:
                remaining = max(0, (end - today).days)

            session.add(
                UserPlanAssignment(
                    user_id=user.id,
                    plan_id=plan.id,
                    start_date=start,
                    end_date=end,
                    status=status,
                    remaining_days=remaining,
                    assigned_at=at_local_noon(start),
                )
            )

        inserted_users += 1
        log.info("assignment seed for %s: %d row(s) created", email, len(rows))

    log.info(
        "assignments: seeded %d user(s) (skipped %d already-seeded)",
        inserted_users,
        len(grouped) - inserted_users,
    )


def main() -> None:
    with Session(engine) as session:
        seed_users(session)
        seed_exercises(session)
        # Users + exercises must be persisted before the template / assignment
        # seeds query for them by id.
        session.flush()
        seed_templates(session)
        session.flush()
        seed_assignments(session)
        session.commit()
    log.info("seed complete.")


if __name__ == "__main__":
    main()
