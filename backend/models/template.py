from typing import Any, List, Optional
from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from .plan import DurationType


def new_id() -> str:
    return str(uuid4())


class PlanTemplate(SQLModel, table=True):
    __tablename__ = "plan_template"

    id: str = Field(default_factory=new_id, primary_key=True)
    title: str = Field(index=True)
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    archived: bool = Field(default=False, nullable=False)

    weekly_plans: Optional[List[Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    flat_days: Optional[List[Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )


class WeeklySplitTemplate(SQLModel, table=True):
    __tablename__ = "weekly_split_template"

    id: str = Field(default_factory=new_id, primary_key=True)
    label: str = Field(index=True)
    days: List[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
