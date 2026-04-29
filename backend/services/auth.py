import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from sqlmodel import Session as DBSession, select

from models import Session, User

# bcrypt's hard limit. Passwords longer than this are silently truncated by
# the algorithm itself; we truncate explicitly so the behaviour is the same
# on hash and verify, and so we don't 500 on a paste of a long string.
BCRYPT_MAX_BYTES = 72

# Cookie / session lifetime. Sliding refresh on each request bumps
# last_used_at; expires_at stays anchored to creation. 30 days is typical
# for "remember me" flows; tune via env if needed.
SESSION_LIFETIME = timedelta(days=30)

# Cookie name used by routers/auth.py + Depends(get_current_user). Centralise
# so a future rename only touches one place.
SESSION_COOKIE_NAME = "vg_session"

def to_bcrypt_bytes(plain: str) -> bytes:
    encoded = plain.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        encoded = encoded[:BCRYPT_MAX_BYTES]
    return encoded


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(to_bcrypt_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(to_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_session(
    db: DBSession,
    user: User,
    *,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> tuple[Session, str]:

    raw_token = secrets.token_urlsafe(32)
    session = Session(
        token_hash=hash_token(raw_token),
        user_id=user.id,
        expires_at=datetime.utcnow() + SESSION_LIFETIME,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def resolve_session(db: DBSession, raw_token: str) -> Optional[User]:
    """Return the user behind a session cookie, or None if not valid.

    Touches `last_used_at` on the session row as a side effect — useful for
    cleaning up stale sessions later.
    """
    if not raw_token:
        return None

    session = db.exec(
        select(Session).where(Session.token_hash == hash_token(raw_token))
    ).first()
    if session is None:
        return None
    if session.expires_at < datetime.utcnow():
        # Expired — drop it eagerly so future lookups don't even hit it.
        db.delete(session)
        db.commit()
        return None
    if session.user is None or session.user.removed:
        return None

    # Best-effort touch — don't let a write race break auth.
    try:
        session.last_used_at = datetime.utcnow()
        db.add(session)
        db.commit()
    except Exception:
        db.rollback()

    return session.user


def revoke_session(db: DBSession, raw_token: str) -> None:
    """Drop the session row matching this token. Idempotent — silent no-op
    if the token doesn't exist."""
    session = db.exec(
        select(Session).where(Session.token_hash == hash_token(raw_token))
    ).first()
    if session is not None:
        db.delete(session)
        db.commit()


def revoke_all_for_user(db: DBSession, user_id: str) -> None:
    """Used by the future password-change / "log out everywhere" flow."""
    sessions = db.exec(select(Session).where(Session.user_id == user_id)).all()
    for s in sessions:
        db.delete(s)
    db.commit()
