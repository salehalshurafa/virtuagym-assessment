from typing import Optional

from pydantic import EmailStr, Field

from models import Gender

from .common import CamelModel


class SignupRequest(CamelModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    timezone: Optional[str] = None
    gender: Optional[Gender] = None
    phone_number: Optional[str] = None


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
