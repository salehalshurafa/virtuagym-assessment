from datetime import date
from typing import List, Optional

from pydantic import EmailStr

from models import DurationType, Gender, User, UserPlanAssignmentStatus

from .common import CamelModel
from .plan import PlanDayRead, WeeklyWorkoutPlanRead
from .schedule import ScheduleEntry


class UserLatestPlanRead(CamelModel):
    id: str
    plan_id: str
    plan_title: str
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    start_date: date
    end_date: date
    status: UserPlanAssignmentStatus
    remaining_days: Optional[int] = None
    assigned_by_name: Optional[str] = None
    assigned_by_email: Optional[str] = None
    weekly_plans: Optional[List[WeeklyWorkoutPlanRead]] = None
    flat_days: Optional[List[PlanDayRead]] = None
    schedule: List[ScheduleEntry] = []


class UserRead(CamelModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    gender: Optional[Gender] = None
    phone_number: Optional[str] = None
    latest_plan: Optional[UserLatestPlanRead] = None
    removed: Optional[bool] = None


class UserUpdate(CamelModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    gender: Optional[Gender] = None
    phone_number: Optional[str] = None


class UserCreate(CamelModel):
    first_name: str
    last_name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    gender: Optional[Gender] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None


def serialize_user(user: User) -> UserRead:
    from services.schedule_service import compute_schedule

    latest_plan: Optional[UserLatestPlanRead] = None

    assignment = user.assignments[0] if user.assignments else None
    if assignment is not None and assignment.plan is not None:
        plan = assignment.plan
        latest_plan = UserLatestPlanRead(
            id=assignment.id,
            plan_id=plan.id,
            plan_title=plan.title,
            duration=plan.duration,
            duration_type=plan.duration_type,
            image_url=plan.image_url,
            workout_days_per_week=plan.workout_days_per_week,
            start_date=assignment.start_date,
            end_date=assignment.end_date,
            status=assignment.status,
            remaining_days=assignment.remaining_days,
            assigned_by_name=assignment.assigned_by_name,
            assigned_by_email=assignment.assigned_by_email,
            weekly_plans=(
                [WeeklyWorkoutPlanRead.model_validate(wp) for wp in plan.weekly_plans]
                if plan.weekly_plans else None
            ),
            flat_days=(
                [PlanDayRead.model_validate(d) for d in plan.flat_days]
                if plan.flat_days else None
            ),
            schedule=compute_schedule(assignment),
        )

    return UserRead(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        avatar_url=user.avatar_url,
        timezone=user.timezone or "UTC",
        gender=user.gender,
        phone_number=user.phone_number,
        latest_plan=latest_plan,
        removed=user.removed if user.removed else None,
    )
