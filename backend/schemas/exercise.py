from typing import Optional

from models import BodyCategory, Equipment

from .common import CamelModel


class ExerciseRead(CamelModel):
    id: str
    name: str
    body_category: BodyCategory
    equipment: Equipment
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    instructions: Optional[str] = None
    usage_count: int


class ExerciseCreate(CamelModel):
    name: str
    body_category: BodyCategory
    equipment: Equipment
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    instructions: Optional[str] = None


class ExerciseUpdate(CamelModel):
    name: Optional[str] = None
    body_category: Optional[BodyCategory] = None
    equipment: Optional[Equipment] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    instructions: Optional[str] = None
