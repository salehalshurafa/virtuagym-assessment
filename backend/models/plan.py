from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

from enum import Enum

if TYPE_CHECKING:
    from .user import UserPlanAssignment


def new_id() -> str:
    return str(uuid4())

class DurationType(str, Enum):
    days = "days"
    weeks = "weeks"
    months = "months"
    years = "years"


class Plan(SQLModel, table=True):
    __tablename__ = "plan"

    id: str = Field(default_factory=new_id, primary_key=True)
    title: str = Field(index=True)
    duration: int
    duration_type: DurationType
    image_url: Optional[str] = None
    workout_days_per_week: Optional[int] = None
    archived: bool = Field(default=False, nullable=False)

    weekly_plans: List["WeeklyWorkoutPlan"] = Relationship(
        back_populates="plan",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "WeeklyWorkoutPlan.order_index",
        },
    )

    flat_days: List["PlanDay"] = Relationship(
        back_populates="plan",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PlanDay.order_index",
            "foreign_keys": "[PlanDay.plan_id]",
        },
    )

    assignments: List["UserPlanAssignment"] = Relationship(
        back_populates="plan",
        sa_relationship_kwargs={"cascade": "all"},
    )


class WeeklyWorkoutPlan(SQLModel, table=True):
    __tablename__ = "weekly_workout_plan"

    id: str = Field(default_factory=new_id, primary_key=True)
    plan_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("plan.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    label: str
    week_frequency: int = Field(default=1, nullable=False)
    order_index: int = Field(default=0, nullable=False)

    plan: "Plan" = Relationship(back_populates="weekly_plans")
    days: List["PlanDay"] = Relationship(
        back_populates="weekly_plan",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PlanDay.order_index",
            "foreign_keys": "[PlanDay.weekly_plan_id]",
        },
    )

class PlanDay(SQLModel, table=True):
    __tablename__ = "plan_day"
    __table_args__ = (
        CheckConstraint(
            "(weekly_plan_id IS NOT NULL AND plan_id IS NULL) OR "
            "(weekly_plan_id IS NULL AND plan_id IS NOT NULL)",
            name="plan_day_exactly_one_parent",
        ),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    weekly_plan_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("weekly_workout_plan.id", ondelete="CASCADE"),
            index=True,
            nullable=True,
        ),
    )
    plan_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("plan.id", ondelete="CASCADE"),
            index=True,
            nullable=True,
        ),
    )
    label: str
    is_rest: bool = Field(default=False, nullable=False)
    order_index: int = Field(default=0, nullable=False)

    weekly_plan: Optional[WeeklyWorkoutPlan] = Relationship(
        back_populates="days",
        sa_relationship_kwargs={"foreign_keys": "[PlanDay.weekly_plan_id]"},
    )
    plan: Optional[Plan] = Relationship(
        back_populates="flat_days",
        sa_relationship_kwargs={"foreign_keys": "[PlanDay.plan_id]"},
    )
    exercises: List["ExerciseAssignment"] = Relationship(
        back_populates="plan_day",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ExerciseAssignment.order_index",
        },
    )

class ExerciseAssignment(SQLModel, table=True):
    __tablename__ = "exercise_assignment"

    id: str = Field(default_factory=new_id, primary_key=True)
    plan_day_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("plan_day.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    exercise_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("exercise.id", ondelete="SET NULL"),
            index=True,
            nullable=True,
        ),
    )
    exercise_name: str
    sets: int = Field(default=3, nullable=False)
    reps: int = Field(default=10, nullable=False)
    weight: Optional[float] = None
    weight_unit: str = Field(default="kg", nullable=False)
    rest_seconds: int = Field(default=60, nullable=False)
    order_index: int = Field(default=0, nullable=False)

    plan_day: PlanDay = Relationship(back_populates="exercises")
