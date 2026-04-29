from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from models import (
    DurationType,
    Exercise,
    ExerciseAssignment,
    Plan,
    PlanDay,
    WeeklyWorkoutPlan,
)
from schemas import (
    ExerciseAssignmentCreate,
    PlanCreate,
    PlanDayCreate,
    WeeklyWorkoutPlanCreate,
)


DAYS_PER = {
    DurationType.days: 1,
    DurationType.weeks: 7,
    DurationType.months: 30,
    DurationType.years: 365,
}


def total_days(duration: int, duration_type: DurationType | str) -> int:
    if isinstance(duration_type, str):
        duration_type = DurationType(duration_type)
    return duration * DAYS_PER[duration_type]


def materialize_exercise_assignment(
    payload: ExerciseAssignmentCreate,
    session: Optional[Session] = None,
) -> ExerciseAssignment:
    exercise_id = payload.exercise_id
    if exercise_id and session is not None and session.get(Exercise, exercise_id) is None:
        exercise_id = None

    return ExerciseAssignment(
        exercise_id=exercise_id,
        exercise_name=payload.exercise_name,
        sets=payload.sets,
        reps=payload.reps,
        weight=payload.weight,
        weight_unit=payload.weight_unit,
        rest_seconds=payload.rest_seconds,
        order_index=payload.order_index,
    )


def materialize_plan_day(
    payload: PlanDayCreate,
    session: Optional[Session] = None,
) -> PlanDay:
    # Per BACKEND_SPEC §6.3: every non-rest day must carry at least one
    # exercise with a non-empty name. We surface this as a ``ValueError``
    # so the route handler can map it to a 400.
    if not payload.is_rest:
        if not payload.exercises:
            raise ValueError(
                f"Day '{payload.label}' is a workout day but has no exercises."
            )
        for ex in payload.exercises:
            if not ex.exercise_name or not ex.exercise_name.strip():
                raise ValueError(
                    f"Day '{payload.label}' has an exercise with no name."
                )

    day = PlanDay(
        label=payload.label,
        is_rest=payload.is_rest,
        order_index=payload.order_index,
    )
    for ex in payload.exercises:
        day.exercises.append(materialize_exercise_assignment(ex, session))
    return day


def materialize_weekly_plan(
    payload: WeeklyWorkoutPlanCreate,
    session: Optional[Session] = None,
) -> WeeklyWorkoutPlan:
    """Build a fresh ``WeeklyWorkoutPlan`` from a ``WeeklyWorkoutPlanCreate``
    payload. The ``plan_id`` FK is set by the caller (``attach_weeks_to_plan``)
    when the weekly is appended onto the parent plan."""
    weekly = WeeklyWorkoutPlan(
        label=payload.label,
        week_frequency=payload.week_frequency,
        order_index=payload.order_index,
    )
    for day_payload in payload.days:
        weekly.days.append(materialize_plan_day(day_payload, session))
    return weekly


def attach_weeks_to_plan(
    session: Session,
    plan: Plan,
    weeks: list[WeeklyWorkoutPlanCreate],
) -> None:
    """Append fresh ``WeeklyWorkoutPlan`` rows to ``plan``. After the
    join-table collapse, every weekly belongs to exactly one plan — there
    is no longer a ``weeklyPlanId`` reference path. Each entry must be
    inline."""
    for entry in weeks:
        weekly = materialize_weekly_plan(entry, session)
        plan.weekly_plans.append(weekly)


def materialize_plan(session: Session, payload: PlanCreate) -> Plan:
    has_weekly = bool(payload.weekly_plans)
    has_flat = bool(payload.flat_days)
    if has_weekly and has_flat:
        raise ValueError("A plan cannot have both weeklyPlans and flatDays — pick one")

    plan = Plan(
        title=payload.title,
        duration=payload.duration,
        duration_type=payload.duration_type,
        image_url=payload.image_url,
        workout_days_per_week=payload.workout_days_per_week,
    )

    if has_weekly:
        attach_weeks_to_plan(session, plan, payload.weekly_plans)
    if has_flat:
        for day_payload in payload.flat_days:
            plan.flat_days.append(materialize_plan_day(day_payload, session))

    return plan
