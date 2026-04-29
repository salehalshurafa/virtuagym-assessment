"""Template ↔ live conversion helpers.

Two directions:

- ``instantiate_plan_template`` reads a ``PlanTemplate`` (JSON-stored) and
  builds a fresh live ``Plan`` + nested ``WeeklyWorkoutPlan`` /
  ``PlanDay`` / ``ExerciseAssignment`` rows. The live tree is independent —
  editing it cannot mutate the template.
- ``serialize_plan_to_template_json`` and ``serialize_weekly_to_template_json``
  walk a live entity and emit the JSON shape that goes into the template
  tables. Used by the post-hoc "Save as template" buttons (B.3).
"""

from __future__ import annotations

from typing import List, Optional

from sqlmodel import Session, select

from models import (
    BodyCategory,
    Equipment,
    Exercise,
    ExerciseAssignment,
    Plan,
    PlanDay,
    PlanTemplate,
    WeeklySplitTemplate,
    WeeklyWorkoutPlan,
)


# ---------------------------------------------------------------------------
# Template → live (instantiate)
# ---------------------------------------------------------------------------


def build_exercise_from_json(payload: dict, order_index: int) -> ExerciseAssignment:
    return ExerciseAssignment(
        exercise_id=payload.get("exerciseId") or payload.get("exercise_id"),
        exercise_name=payload.get("exerciseName") or payload.get("exercise_name") or "",
        sets=int(payload.get("sets", 3)),
        reps=int(payload.get("reps", 10)),
        weight=payload.get("weight"),
        weight_unit=payload.get("weightUnit") or payload.get("weight_unit") or "kg",
        rest_seconds=int(payload.get("restSeconds") or payload.get("rest_seconds") or 60),
        order_index=int(payload.get("orderIndex", order_index)),
    )


def build_day_from_json(payload: dict, order_index: int) -> PlanDay:
    day = PlanDay(
        label=payload.get("label", f"Day {order_index + 1}"),
        is_rest=bool(payload.get("isRest") or payload.get("is_rest") or False),
        order_index=int(payload.get("orderIndex", order_index)),
    )
    for i, ex in enumerate(payload.get("exercises", []) or []):
        day.exercises.append(build_exercise_from_json(ex, i))
    return day


def build_weekly_from_json(
    label: str,
    days_payload: List[dict],
    week_frequency: int,
    order_index: int,
) -> WeeklyWorkoutPlan:
    weekly = WeeklyWorkoutPlan(
        label=label,
        week_frequency=week_frequency,
        order_index=order_index,
    )
    for i, d in enumerate(days_payload or []):
        weekly.days.append(build_day_from_json(d, i))
    return weekly


def instantiate_plan_template(session: Session, template: PlanTemplate) -> Plan:
    """Materialize a fresh live Plan from a PlanTemplate.

    Each weekly inside the template becomes a fresh ``WeeklyWorkoutPlan``
    row attached directly to the new ``Plan`` (no join table). Editing
    the new plan never mutates the template; deleting the template never
    affects the plan.
    """
    plan = Plan(
        title=template.title,
        duration=template.duration,
        duration_type=template.duration_type,
        image_url=template.image_url,
        workout_days_per_week=template.workout_days_per_week,
    )

    if template.weekly_plans:
        for i, entry in enumerate(template.weekly_plans):
            ref_id = entry.get("weeklySplitTemplateId") or entry.get(
                "weekly_split_template_id"
            )
            week_frequency = int(
                entry.get("weekFrequency") or entry.get("week_frequency") or 1
            )
            order_index = int(entry.get("orderIndex", i))
            if ref_id:
                ref = session.get(WeeklySplitTemplate, ref_id)
                if ref is None:
                    raise ValueError(
                        f"Weekly split template {ref_id} not found inside plan template"
                    )
                weekly = build_weekly_from_json(
                    ref.label, ref.days or [], week_frequency, order_index,
                )
            else:
                weekly = build_weekly_from_json(
                    entry.get("label", f"Weekly Workout Plan {i + 1}"),
                    entry.get("days") or [],
                    week_frequency,
                    order_index,
                )
            plan.weekly_plans.append(weekly)
    elif template.flat_days:
        for i, d in enumerate(template.flat_days):
            plan.flat_days.append(build_day_from_json(d, i))

    return plan


# ---------------------------------------------------------------------------
# Live → template (serialize)
# ---------------------------------------------------------------------------


def exercise_to_json(ex: ExerciseAssignment) -> dict:
    return {
        "exerciseId": ex.exercise_id,
        "exerciseName": ex.exercise_name,
        "sets": ex.sets,
        "reps": ex.reps,
        "weight": ex.weight,
        "weightUnit": ex.weight_unit,
        "restSeconds": ex.rest_seconds,
        "orderIndex": ex.order_index,
    }


def day_to_json(day: PlanDay) -> dict:
    return {
        "label": day.label,
        "isRest": day.is_rest,
        "orderIndex": day.order_index,
        "exercises": [exercise_to_json(e) for e in day.exercises],
    }


def serialize_weekly_to_template_json(weekly: WeeklyWorkoutPlan) -> List[dict]:
    """Walk a live WeeklyWorkoutPlan into the JSON shape stored on
    ``WeeklySplitTemplate.days``."""
    return [day_to_json(d) for d in weekly.days]


def serialize_plan_to_template_json(plan: Plan) -> dict:
    """Build the JSON shape that goes onto a ``PlanTemplate``.

    Returns a dict with two keys (``weekly_plans``, ``flat_days``); exactly
    one is populated.
    """
    if plan.weekly_plans:
        return {
            "weekly_plans": [
                {
                    "label": wp.label,
                    "days": serialize_weekly_to_template_json(wp),
                    "weekFrequency": wp.week_frequency,
                    "orderIndex": wp.order_index,
                }
                for wp in plan.weekly_plans
            ],
            "flat_days": None,
        }
    return {
        "weekly_plans": None,
        "flat_days": [day_to_json(d) for d in plan.flat_days],
    }


# ---------------------------------------------------------------------------
# Library exercise cascade for the post-hoc weekly-template promotion (B.3)
# ---------------------------------------------------------------------------


def cascade_library_exercises_for_week(session: Session, weekly: WeeklyWorkoutPlan) -> int:
    """For every exercise inside ``weekly``, ensure a matching row exists in
    the ``exercise`` library. Returns the number of new rows inserted.

    The library schema after B.8 is name-only — no fabricated sets/reps
    defaults. Image / video / instructions stay null and the admin can fill
    them in later.
    """
    existing_names = {
        n for (n,) in session.exec(select(Exercise.name)).all()
    }
    inserted = 0
    seen: set[str] = set()
    for day in weekly.days:
        for ex in day.exercises:
            name = (ex.exercise_name or "").strip()
            if not name or name in existing_names or name in seen:
                continue
            seen.add(name)
            session.add(
                Exercise(
                    name=name,
                    body_category=BodyCategory.cardio,  # neutral default; admin retags later
                    equipment=Equipment.free_weight,
                )
            )
            inserted += 1
    return inserted
