"""Schedule computation.

Given a UserPlanAssignment, walk its Plan structure and produce dated
ScheduleEntry rows from start_date up to (and including) end_date.

Used by:
  - GET /api/assignments/{id}/schedule
  - serialize_user (so each user's latestPlan carries its dated schedule)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from models import PlanDay, UserPlanAssignment, WeeklyWorkoutPlan
from schemas.schedule import ScheduleEntry, ScheduleExercise


def materialize_entry(day: PlanDay, on: date) -> ScheduleEntry:
    return ScheduleEntry(
        date=on,
        day_id=day.id,
        label=day.label,
        is_rest=day.is_rest,
        exercises=[
            ScheduleExercise(
                id=ex.id,
                exercise_id=ex.exercise_id,
                exercise_name=ex.exercise_name,
                sets=ex.sets,
                reps=ex.reps,
                weight=ex.weight,
                weight_unit=ex.weight_unit,
                rest_seconds=ex.rest_seconds,
                order_index=ex.order_index,
            )
            for ex in sorted(day.exercises, key=lambda e: e.order_index)
        ],
    )


def compute_schedule(assignment: UserPlanAssignment) -> List[ScheduleEntry]:
    """Walk the plan's structure and emit one ScheduleEntry per calendar day,
    from `assignment.start_date` to `assignment.end_date` (inclusive).

    - Weekly mode: iterate plan.weekly_plans in order_index, repeat each
      weekly's days week_frequency times. The whole rotation cycles until
      we've covered every calendar day in the assignment window — so a 4-week
      plan with one weekly at frequency=1 still emits 28 days, not 7.
    - Flat mode: walk flat_days in order_index.

    Stops early if we run out of structure (no template days at all) so we
    don't loop forever.
    """
    plan = assignment.plan
    if not plan:
        return []

    start = assignment.start_date
    end = assignment.end_date
    entries: List[ScheduleEntry] = []

    weeks: List[WeeklyWorkoutPlan] = sorted(
        plan.weekly_plans or [], key=lambda w: w.order_index
    )
    flat_days: List[PlanDay] = sorted(
        plan.flat_days or [], key=lambda d: d.order_index
    )

    if weeks:
        # Cycle the full rotation until every day in the window is covered.
        # `cycle_emitted_days` guards against the pathological case where
        # every weekly ends up with no days (would otherwise loop forever).
        while start <= end:
            cycle_emitted_days = 0
            for weekly in weeks:
                weekly_days = sorted(weekly.days, key=lambda d: d.order_index)
                if not weekly_days:
                    continue
                for _ in range(max(1, weekly.week_frequency)):
                    for day in weekly_days:
                        if start > end:
                            return entries
                        entries.append(materialize_entry(day, start))
                        start += timedelta(days=1)
                        cycle_emitted_days += 1
            if cycle_emitted_days == 0:
                break
    elif flat_days:
        for day in flat_days:
            if start > end:
                break
            entries.append(materialize_entry(day, start))
            start += timedelta(days=1)

    return entries
