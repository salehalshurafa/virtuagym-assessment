"""Shared FastAPI dependencies — currently the auth resolver.

`get_current_user` is the single source of truth for "who is making this
request". Every protected router declares it via `Depends(get_current_user)`
or via a router-level `dependencies=[Depends(get_current_user)]`.

The dependency requires a valid session cookie. There is no env-based
fallback — every protected request must carry one. Tests that need a
fixed identity override `get_current_user` in the FastAPI app's
dependency-override map (see `tests/conftest.py::stub_current_user`).
"""

from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session as DBSession

from db import get_session
from models import User
from services.auth import SESSION_COOKIE_NAME, resolve_session


def get_current_user(
    session: DBSession = Depends(get_session),
    vg_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User:
    if vg_session:
        user = resolve_session(session, vg_session)
        if user is not None:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_current_user_optional(
    session: DBSession = Depends(get_session),
    vg_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Optional[User]:
    """Same as get_current_user but returns None instead of 401. Used by
    `/api/auth/me` so an unauthenticated probe doesn't blow up logs."""
    if vg_session:
        return resolve_session(session, vg_session)
    return None
