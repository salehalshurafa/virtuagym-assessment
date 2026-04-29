from datetime import date
from typing import List, Optional

from models import DurationType

from .common import CamelModel
from .plan import PlanDayCreate

class WeeklySplitTemplateRead(CamelModel):
    id: str
    label: str
    days: List[PlanDayCreate] = []


class WeeklySplitTemplateCreate(CamelModel):
    label: str
    days: List[PlanDayCreate] = []


class WeeklySplitTemplateUpdate(CamelModel):
    label: Optional[str] = None
    days: Optional[List[PlanDayCreate]] = None


class WeeklySplitTemplateFromWeeklyPlanRequest(CamelModel):
    weekly_plan_id: str
    label: Optional[str] = None

class PlanTemplateWeeklyEntry(CamelModel):
    weekly_split_template_id: Optional[str] = None
    label: Optional[str] = None
    days: Optional[List[PlanDayCreate]] = None
    week_frequency: int = 1
    order_index: int = 0

class PlanTemplateRead(CamelModel):
    id: str
    title: str
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    archived: bool = False
    weekly_plans: Optional[List[PlanTemplateWeeklyEntry]] = None
    flat_days: Optional[List[PlanDayCreate]] = None


class PlanTemplateCreate(CamelModel):
    title: str
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    weekly_plans: Optional[List[PlanTemplateWeeklyEntry]] = None
    flat_days: Optional[List[PlanDayCreate]] = None


class PlanTemplateUpdate(CamelModel):
    title: Optional[str] = None
    duration: Optional[int] = None
    duration_type: Optional[DurationType] = None
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    weekly_plans: Optional[List[PlanTemplateWeeklyEntry]] = None
    flat_days: Optional[List[PlanDayCreate]] = None


class PlanTemplateFromPlanRequest(CamelModel):
    plan_id: str
    title: Optional[str] = None


class PlanFromTemplateRequest(CamelModel):
    template_id: str
    start_date: date
    user_ids: List[str] = []
    force_replace_user_ids: List[str] = []
