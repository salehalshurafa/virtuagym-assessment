from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlmodel import Session as DBSession, select

from config import get_settings
from db import get_session
from models import User
from schemas import LoginRequest, SignupRequest, UserRead, serialize_user
from services.auth import (
    SESSION_COOKIE_NAME,
    SESSION_LIFETIME,
    create_session,
    hash_password,
    revoke_session,
    verify_password,
)

from .deps import get_current_user_optional

router = APIRouter(tags=["auth"])


def set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.post(
    "/signup",
    response_model=UserRead,
    response_model_exclude_none=True,
    status_code=201,
)
def signup(
    payload: SignupRequest,
    response: Response,
    request: Request,
    session: DBSession = Depends(get_session),
) -> UserRead:
   
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        )

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        timezone=payload.timezone or "UTC",
        gender=payload.gender,
        phone_number=payload.phone_number,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    _, raw_token = create_session(
        session,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookie(response, raw_token)
    return serialize_user(user)


@router.post(
    "/login",
    response_model=UserRead,
    response_model_exclude_none=True,
)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    session: DBSession = Depends(get_session),
) -> UserRead:
    user = session.exec(select(User).where(User.email == payload.email)).first()
    valid = verify_password(payload.password, user.password_hash if user else None)
    if user is None or user.removed or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    _, raw_token = create_session(
        session,
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookie(response, raw_token)
    return serialize_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: DBSession = Depends(get_session),
    vg_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    if vg_session:
        revoke_session(session, vg_session)
    clear_session_cookie(response)


@router.get(
    "/me",
    response_model=UserRead,
    response_model_exclude_none=True,
)
def me(
    user: Optional[User] = Depends(get_current_user_optional),
) -> UserRead:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return serialize_user(user)
