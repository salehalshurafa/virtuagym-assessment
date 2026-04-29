"""Unit tests for ``schemas.user.serialize_user``."""

from __future__ import annotations

from models import Gender, User
from schemas.user import serialize_user


def make_user(**overrides) -> User:
    # **overrides are some fields that are optional that can be passed to a 
    # created user but are not required to create a user
    defaults = dict(
        id="u1",
        first_name="Alex",
        last_name="Tester",
        email="alex@test.example",
        timezone="Europe/Amsterdam",
    )
    defaults.update(overrides)
    return User(**defaults)


def test_serialize_user_with_no_assignments_omits_latest_plan():
    """A user that's never been assigned a plan should serialize with
    ``latest_plan=None``."""

    user = make_user()
    user.assignments = []

    result = serialize_user(user)

    assert result.latest_plan is None
    assert result.id == "u1"
    assert result.email == "alex@test.example"


def test_serialize_user_active_user_omits_removed_field():
    """``removed`` is an optional field that is set to true only when
    a user gets soft-deleted. For a user who is active, remove=False, there
    is no need to return removed, we can omit it as None."""

    user = make_user(removed=False)
    user.assignments = []

    result = serialize_user(user)

    assert result.removed is None


def test_serialize_user_removed_user_carries_flag():
    """A soft-deleted user must serialize with ``removed=True``."""

    user = make_user(removed=True)
    user.assignments = []

    result = serialize_user(user)

    assert result.removed is True


def test_serialize_user_defaults_missing_timezone_to_utc():
    """Timezone defaults to``"UTC"`` when there is no explicitly 
    set timezone."""

    user = make_user(timezone=None)
    user.assignments = []

    result = serialize_user(user)

    assert result.timezone == "UTC"


def test_serialize_user_preserves_explicit_timezone():
    """A real timezone passes through untouched."""
    
    user = make_user(timezone="Asia/Tokyo")
    user.assignments = []

    result = serialize_user(user)

    assert result.timezone == "Asia/Tokyo"


def test_serialize_user_passes_through_optional_profile_fields():
    """Gender, phone, and avatar_url are optional profile fields. None 
    should stay as None, and populated should stay populated. Nones are
    excluded from returned response."""
    
    user = make_user(
        gender=Gender.female,
        phone_number="+31 6 1234 5678",
        avatar_url="data:image/png;base64,abc",
    )
    user.assignments = []

    result = serialize_user(user)

    assert result.gender == Gender.female
    assert result.phone_number == "+31 6 1234 5678"
    assert result.avatar_url == "data:image/png;base64,abc"
