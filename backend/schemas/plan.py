from typing import List, Optional
from models import DurationType, Plan, UserPlanAssignmentStatus
from .common import CamelModel


class ExerciseAssignmentRead(CamelModel):
    id: str
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: int
    reps: int
    weight: Optional[float] = None
    weight_unit: str
    rest_seconds: int
    order_index: int


class ExerciseAssignmentCreate(CamelModel):
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: int = 3
    reps: int = 10
    weight: Optional[float] = None
    weight_unit: str = "kg"
    rest_seconds: int = 60
    order_index: int = 0


class ExerciseAssignmentUpdate(CamelModel):
    exercise_id: Optional[str] = None
    exercise_name: Optional[str] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    rest_seconds: Optional[int] = None
    order_index: Optional[int] = None


class PlanDayRead(CamelModel):
    id: str
    label: str
    is_rest: bool
    order_index: int
    exercises: List[ExerciseAssignmentRead] = []


class PlanDayCreate(CamelModel):
    label: str
    is_rest: bool = False
    order_index: int = 0
    exercises: List[ExerciseAssignmentCreate] = []


class PlanDayUpdate(CamelModel):
    label: Optional[str] = None
    is_rest: Optional[bool] = None
    order_index: Optional[int] = None


class WeeklyWorkoutPlanRead(CamelModel):
    id: str
    plan_id: str
    label: str
    week_frequency: int
    order_index: int
    days: List[PlanDayRead] = []


class WeeklyWorkoutPlanCreate(CamelModel):
    label: str
    week_frequency: int = 1
    order_index: int = 0
    days: List[PlanDayCreate] = []


class WeeklyWorkoutPlanUpdate(CamelModel):
    label: Optional[str] = None
    week_frequency: Optional[int] = None
    order_index: Optional[int] = None
    days: Optional[List[PlanDayCreate]] = None


class PlanRead(CamelModel):
    id: str
    title: str
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    archived: bool = False
    user_count: int = 0
    weekly_plans: Optional[List[WeeklyWorkoutPlanRead]] = None
    flat_days: Optional[List[PlanDayRead]] = None


class PlanCreate(CamelModel):
    title: str
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    weekly_plans: Optional[List[WeeklyWorkoutPlanCreate]] = None
    flat_days: Optional[List[PlanDayCreate]] = None


class PlanUpdate(CamelModel):
    title: Optional[str] = None
    duration: Optional[int] = None
    duration_type: Optional[DurationType] = None
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    weekly_plans: Optional[List[WeeklyWorkoutPlanCreate]] = None
    flat_days: Optional[List[PlanDayCreate]] = None


def serialize_plan(plan: Plan) -> PlanRead:
    return PlanRead(
        id=plan.id,
        title=plan.title,
        duration=plan.duration,
        duration_type=plan.duration_type,
        image_url=plan.image_url,
        workout_days_per_week=plan.workout_days_per_week,
        archived=plan.archived,
        user_count=len([
            a for a in plan.assignments
            if a.status in (UserPlanAssignmentStatus.in_progress, UserPlanAssignmentStatus.paused)
        ]),
        weekly_plans=(
            [WeeklyWorkoutPlanRead.model_validate(wp) for wp in plan.weekly_plans]
            if plan.weekly_plans else None
        ),
        flat_days=(
            [PlanDayRead.model_validate(d) for d in plan.flat_days]
            if plan.flat_days else None
        ),
    )
