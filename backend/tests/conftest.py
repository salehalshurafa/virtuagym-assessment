"""Shared pytest fixtures.

Strategy
--------
Tests run against an in-memory SQLite database. Reasons:
- No Postgres dependency in CI.
- Fresh schema per test, so failures don't bleed across cases.
- Fast (no network).

Caveats
-------
Two Postgres-specific features get skipped on SQLite:
1. The partial unique index `uq_one_active_assignment_per_user` is a noop;
   SQLAlchemy's `postgresql_where=...` is dialect-gated.
2. Postgres ENUM types fall back to Python string enums.

Tests that depend on those features should mark themselves as
`@pytest.mark.postgres_only` and skip on SQLite.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Generator, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

# Importing models registers the tables on SQLModel.metadata. Don't drop these
# imports even if the IDE flags them as unused — they are the side-effect.
import models
from db import get_session
from main import app
from models import User
from routers.deps import get_current_user, get_current_user_optional
from services.auth import hash_password
from services.mailer import get_mailer


@pytest.fixture(scope="function")
def engine_fixture():
    """Brand-new SQLite engine per test. StaticPool keeps the in-memory DB
    alive across the multiple connections SQLAlchemy may open."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine_fixture) -> Generator[Session, None, None]:
    with Session(engine_fixture) as s:
        yield s


@pytest.fixture
def client(engine_fixture) -> Generator[TestClient, None, None]:
    """TestClient with the get_session dep wired to the test engine. The
    auth dep is left alone — tests that need a logged-in user use the
    `auth_client` fixture below."""

    def override() -> Generator[Session, None, None]:
        with Session(engine_fixture) as s:
            yield s

    app.dependency_overrides[get_session] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def seed_user(session: Session):
    """Insert a known admin-equivalent user so signup / cookie tests have
    something deterministic to log in as."""
    from models import User

    user = User(
        first_name="Test",
        last_name="Admin",
        email="admin@test.example",
        password_hash=hash_password("TestPass!23"),
        timezone="UTC",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_client(client: TestClient, seed_user) -> TestClient:
    """TestClient with a real session cookie set via the login endpoint.

    Uses TestClient's cookie jar — every subsequent request automatically
    includes the cookie, so individual tests don't have to thread it
    through manually.
    """
    res = client.post(
        "/api/auth/login",
        json={"email": seed_user.email, "password": "TestPass!23"},
    )
    assert res.status_code == 200, res.text
    return client


@pytest.fixture
def stub_current_user(seed_user):
    """For tests that don't care about the auth path and just want every
    request to resolve to seed_user. Bypasses the cookie machinery
    entirely."""

    def resolve():
        return seed_user

    app.dependency_overrides[get_current_user] = resolve
    app.dependency_overrides[get_current_user_optional] = resolve
    yield seed_user
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_optional, None)


# A replica of the mailing services for testing, no actual SMTP here
class FakeMailer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def send_plan_assigned(
        self, to: str, plan, *, actor: Optional[User] = None
    ) -> None:
        self.calls.append(("plan_assigned", {"to": to, "title": plan.title}))

    async def send_plan_modified(
        self, to: str, plan, *, actor: Optional[User] = None, changes=None
    ) -> None:
        self.calls.append(("plan_modified", {"to": to, "title": plan.title}))

    async def send_plan_archived(
        self, to: str, plan_title: str, *, actor: Optional[User] = None
    ) -> None:
        self.calls.append(("plan_archived", {"to": to, "title": plan_title}))

    async def send_plan_paused(
        self, to: str, plan, *, actor: Optional[User] = None
    ) -> None:
        self.calls.append(("plan_paused", {"to": to, "title": plan.title}))

    async def send_plan_resumed(
        self, to: str, plan, end_date, *, actor: Optional[User] = None
    ) -> None:
        self.calls.append(("plan_resumed", {"to": to, "title": plan.title}))

    async def send_plan_cancelled(
        self, to: str, plan, *, actor: Optional[User] = None
    ) -> None:
        self.calls.append(("plan_cancelled", {"to": to, "title": plan.title}))

    async def send_plan_restarted(
        self, to: str, plan, start_date, end_date, *, actor: Optional[User] = None
    ) -> None:
        self.calls.append(("plan_restarted", {"to": to, "title": plan.title}))

    async def send_user_account_created(
        self, to: str, new_user_first_name: str, *, creator: User
    ) -> None:
        self.calls.append(
            ("user_account_created", {"to": to, "name": new_user_first_name})
        )


@pytest.fixture
def fake_mailer() -> Iterator[FakeMailer]:
    """Override ``get_mailer`` with a ``FakeMailer`` instance for the
    duration of the test. Cleans up the override on teardown so the
    next test isn't poisoned with a stale recorder."""
    fm = FakeMailer()
    app.dependency_overrides[get_mailer] = lambda: fm
    yield fm
    app.dependency_overrides.pop(get_mailer, None)


@pytest.fixture
def assignee(session: Session) -> User:
    """A plain non-admin user that tests can target as the *subject* of a
    flow (assignment, profile edit, etc.). Distinct from ``seed_user``
    (the admin who acts via ``stub_current_user``) so the actor / subject
    distinction stays clean in assertions."""
    user = User(
        first_name="Eve",
        last_name="Assignee",
        email="eve@test.example",
        timezone="UTC",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
