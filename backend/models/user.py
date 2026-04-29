from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Index, text
from sqlmodel import Field, Relationship, SQLModel

from enum import Enum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

if TYPE_CHECKING:
    from .auth import Session
    from .plan import Plan


def new_id() -> str:
    return str(uuid4())


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: str = Field(default_factory=new_id, primary_key=True)
    first_name: str
    last_name: str
    email: str = Field(index=True, unique=True)
    avatar_url: Optional[str] = None
    removed: bool = Field(default=False, nullable=False)
    password_hash: Optional[str] = None
    timezone: str = Field(default="UTC", nullable=False)
    gender: Optional[Gender] = Field(
        default=None,
        sa_column=Column(
            SAEnum(
                Gender,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
                name="gender",
            ),
            nullable=True,
        ),
    )
    phone_number: Optional[str] = None

    assignments: list["UserPlanAssignment"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all",
            "order_by": "UserPlanAssignment.assigned_at.desc()",
        },
    )

    sessions: list["Session"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

class UserPlanAssignmentStatus(str, Enum):
    in_progress = "in-progress"
    completed = "completed"
    cancelled = "cancelled"
    paused = "paused"

class UserPlanAssignment(SQLModel, table=True):
    __tablename__ = "user_plan_assignment"

    __table_args__ = (
        Index(
            "uq_one_active_assignment_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('in-progress')"),
        ),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: Optional[str] = Field(
        default=None,
         sa_column=Column(String, ForeignKey("user.id", ondelete="CASCADE"),
                         index=True, nullable=False)
    )
    plan_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("plan.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    start_date: date
    end_date: date
    status: UserPlanAssignmentStatus = Field(
        default=UserPlanAssignmentStatus.in_progress,
        sa_column=Column(
            SAEnum(
                UserPlanAssignmentStatus,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
                name="user_plan_assignment_status",
            ),
            nullable=False,
        ),
    )
    remaining_days: Optional[int] = None
    assigned_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    assigned_by_name: Optional[str] = None
    assigned_by_email: Optional[str] = None

    user: User = Relationship(back_populates="assignments")
    plan: "Plan" = Relationship(back_populates="assignments")
