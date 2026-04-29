from datetime import date, datetime
from typing import List, Optional

from models import UserPlanAssignment, UserPlanAssignmentStatus

from .common import CamelModel


class UserPlanAssignmentRead(CamelModel):
    id: str
    user_id: str
    plan_id: str
    plan_title: str
    start_date: date
    end_date: date
    status: UserPlanAssignmentStatus
    remaining_days: Optional[int] = None
    assigned_at: datetime
    assigned_by_name: Optional[str] = None
    assigned_by_email: Optional[str] = None


class UserPlanAssignmentCreate(CamelModel):
    user_id: str
    plan_id: str
    start_date: date


class UserPlanAssignmentUpdate(CamelModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class RepointMultiRequest(CamelModel):
    plan_id: str
    assignment_ids: List[str]


class RepointResult(CamelModel):
    assignment_id: str
    success: bool
    error: Optional[str] = None


class RepointMultiResponse(CamelModel):
    plan_id: str
    results: List[RepointResult]


class BulkAssignConflict(CamelModel):
    plan_title: str


class BulkAssignResult(CamelModel):
    user_id: str
    success: bool
    reason: Optional[str] = None
    assignment_id: Optional[str] = None
    conflict_with: Optional[BulkAssignConflict] = None


class BulkAssignRequest(CamelModel):
    plan_id: str
    start_date: date
    user_ids: List[str]
    force_replace_user_ids: List[str] = []


class BulkAssignResponse(CamelModel):
    plan_id: str
    results: List[BulkAssignResult]


def serialize_assignment(a: UserPlanAssignment) -> UserPlanAssignmentRead:
    return UserPlanAssignmentRead(
        id=a.id,
        user_id=a.user_id,
        plan_id=a.plan_id,
        plan_title=a.plan.title if a.plan else "",
        start_date=a.start_date,
        end_date=a.end_date,
        status=a.status,
        remaining_days=a.remaining_days,
        assigned_at=a.assigned_at,
        assigned_by_name=a.assigned_by_name,
        assigned_by_email=a.assigned_by_email,
    )
