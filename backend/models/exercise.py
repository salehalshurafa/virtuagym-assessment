from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel

from enum import Enum

def new_id() -> str:
    return str(uuid4())


class WeightUnit(str, Enum):
    kg = "kg"
    lbs = "lbs"


class BodyCategory(str, Enum):
    chest = "chest"
    back = "back"
    legs = "legs"
    core = "core"
    arms = "arms"
    shoulders = "shoulders"
    cardio = "cardio"


class Equipment(str, Enum):
    bar = "bar"
    dumbbell = "dumbbell"
    machine = "machine"
    cable = "cable"
    free_weight = "free-weight"


class Exercise(SQLModel, table=True):
    __tablename__ = "exercise"

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str = Field(index=True)
    body_category: BodyCategory
    equipment: Equipment = Field(
        sa_column=Column(
            SAEnum(
                Equipment,
                values_callable=lambda enum_cls: [m.value for m in enum_cls],
                name="equipment",
            ),
            nullable=False,
        ),
    )
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    instructions: Optional[str] = None
    usage_count: int = Field(default=0, nullable=False)
