"""Pause / resume / cancel / restart unit tests for assignment_service."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from models import (
    DurationType,
    Plan,
    UserPlanAssignment,
    UserPlanAssignmentStatus,
)
from services import assignment_service


def make_assignment(start: date, end: date, status: UserPlanAssignmentStatus):
    return UserPlanAssignment(
        user_id="u",
        plan_id="p",
        start_date=start,
        end_date=end,
        status=status,
    )


def make_plan(duration: int, dt: DurationType) -> Plan:
    return Plan(title="P", duration=duration, duration_type=dt)


def test_pause_sets_remaining_days():
    """Pausing an in-progress assignment flips status to ``paused`` and
    records ``remaining_days = end_date - today``."""
    
    today = date(2026, 4, 27)
    a = make_assignment(today - timedelta(days=10), today + timedelta(days=5), UserPlanAssignmentStatus.in_progress)
    assignment_service.pause(a, today=today)
    assert a.status == UserPlanAssignmentStatus.paused
    assert a.remaining_days == 5


def test_pause_rejects_non_in_progress():
    """Calling ``pause`` on an assignment that isn't in-progress raises
    ``HTTPException`` with status 409."""

    today = date(2026, 4, 27)
    a = make_assignment(today, today + timedelta(days=10), UserPlanAssignmentStatus.paused)
    with pytest.raises(HTTPException) as exc:
        assignment_service.pause(a, today=today)
    assert exc.value.status_code == 409


def test_resume_reanchors_end_date_to_today_plus_remaining():
    """Resuming a paused assignment flips status to ``in_progress``, sets
    ``end_date = today + remaining_days``, and clears ``remaining_days``."""

    today = date(2026, 4, 27)
    a = make_assignment(today - timedelta(days=30), today - timedelta(days=15), UserPlanAssignmentStatus.paused)
    a.remaining_days = 7
    assignment_service.resume(a, today=today)
    assert a.status == UserPlanAssignmentStatus.in_progress
    assert a.end_date == today + timedelta(days=7)
    assert a.remaining_days is None


def test_cancel_sets_cancel_state():
    """Cancelling an in-progress assignment sets status to ``cancelled``
    and clears ``remaining_days``."""

    today = date(2026, 4, 27)
    a = make_assignment(today - timedelta(days=5), today + timedelta(days=10), UserPlanAssignmentStatus.in_progress)
    assignment_service.cancel(a)
    assert a.status == UserPlanAssignmentStatus.cancelled
    assert a.remaining_days is None


def test_cancel_rejects_completed():
    """Calling ``cancel`` on a completed assignment raises
    ``HTTPException`` with status 409."""

    today = date(2026, 4, 27)
    a = make_assignment(today - timedelta(days=30), today - timedelta(days=15), UserPlanAssignmentStatus.completed)
    with pytest.raises(HTTPException) as exc:
        assignment_service.cancel(a)
    assert exc.value.status_code == 409


def test_restart_rebases_to_today_plus_plan_duration():
    """Restarting resets ``start_date`` to today, ``end_date`` to today +
    the plan's total duration in days, status to ``in_progress``, and
    clears any leftover ``remaining_days``."""

    today = date(2026, 4, 27)
    a = make_assignment(date(2025, 1, 1), date(2025, 1, 30), UserPlanAssignmentStatus.cancelled)
    a.remaining_days = 99  # garbage from a previous lifecycle
    plan = make_plan(8, DurationType.weeks)
    assignment_service.restart(a, plan, today=today)
    assert a.status == UserPlanAssignmentStatus.in_progress
    assert a.start_date == today
    assert a.end_date == today + timedelta(days=8 * 7)
    assert a.remaining_days is None
