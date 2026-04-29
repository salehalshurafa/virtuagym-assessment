from datetime import date
from typing import List, Optional

from .common import CamelModel


class ScheduleExercise(CamelModel):
    id: str
    exercise_id: Optional[str] = None
    exercise_name: str
    sets: int
    reps: int
    weight: Optional[float] = None
    weight_unit: str
    rest_seconds: int
    order_index: int


class ScheduleEntry(CamelModel):
    date: date
    day_id: str
    label: str
    is_rest: bool
    exercises: List[ScheduleExercise] = []
