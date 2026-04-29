"""Pause / Resume / Cancel / Restart math for UserPlanAssignment.

Pure functions where possible — they take an assignment (and sometimes the
related plan) and mutate it. Caller commits.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status

from models import Plan, UserPlanAssignment, UserPlanAssignmentStatus
from models.user import utcnow
from services.plan_service import total_days


def pause(assignment: UserPlanAssignment, today: date | None = None) -> None:
    if assignment.status != UserPlanAssignmentStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot pause an assignment whose status is '{assignment.status.value}'",
        )
    today = today or date.today()
    remaining = (assignment.end_date - today).days
    assignment.status = UserPlanAssignmentStatus.paused
    assignment.remaining_days = max(0, remaining)


def resume(assignment: UserPlanAssignment, today: date | None = None) -> None:
    if assignment.status != UserPlanAssignmentStatus.paused:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot resume an assignment whose status is '{assignment.status.value}'",
        )
    today = today or date.today()
    remaining = assignment.remaining_days or 0
    assignment.status = UserPlanAssignmentStatus.in_progress
    assignment.end_date = today + timedelta(days=remaining)
    assignment.remaining_days = None
    # Reactivating an assignment makes it the user's latest again.
    assignment.assigned_at = utcnow()


def cancel(assignment: UserPlanAssignment) -> None:
    if assignment.status not in (
        UserPlanAssignmentStatus.in_progress,
        UserPlanAssignmentStatus.paused,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel an assignment whose status is '{assignment.status.value}'",
        )
    assignment.status = UserPlanAssignmentStatus.cancelled
    assignment.remaining_days = None


def restart(assignment: UserPlanAssignment, plan: Plan, today: date | None = None) -> None:
    """Reset start to today and end to today + plan_total_days. Allowed from any status."""
    today = today or date.today()
    duration_days = total_days(plan.duration, plan.duration_type)
    assignment.start_date = today
    assignment.end_date = today + timedelta(days=duration_days)
    assignment.status = UserPlanAssignmentStatus.in_progress
    assignment.remaining_days = None
    # Restarting refreshes the "latest" anchor — same record, but it's now
    # the user's currently-active plan.
    assignment.assigned_at = utcnow()
