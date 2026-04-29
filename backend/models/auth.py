from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


def new_id() -> str:
    return str(uuid4())


class Session(SQLModel, table=True):
    __tablename__ = "session"

    id: str = Field(default_factory=new_id, primary_key=True)
    token_hash: str = Field(index=True, unique=True, nullable=False)
    user_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String,
            ForeignKey("user.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    expires_at: datetime = Field(nullable=False)
    last_used_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

    user: "User" = Relationship(back_populates="sessions")
