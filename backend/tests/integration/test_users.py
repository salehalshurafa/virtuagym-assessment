"""Testing some of the user CRUD operations in addition to some authentication flows"""

from __future__ import annotations


def test_create_user_with_password_can_log_in(client, stub_current_user):
    """Admin-create flow: POST /api/users issues a temp password the new
    user can immediately use to sign in."""
    
    res = client.post(
        "/api/users",
        json={
            "firstName": "Made",
            "lastName": "ByAdmin",
            "email": "made@test.example",
            "timezone": "Europe/Berlin",
            "password": "TempPass!23",
        },
    )
    assert res.status_code == 201, res.text
    new_id = res.json()["id"]

    # Drop the admin override and log in as the new user.
    from main import app
    from routers.deps import get_current_user, get_current_user_optional

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_optional, None)

    login_res = client.post(
        "/api/auth/login",
        json={"email": "made@test.example", "password": "TempPass!23"},
    )
    assert login_res.status_code == 200, login_res.text
    assert login_res.json()["id"] == new_id


def test_user_list_includes_removed_with_flag(client, stub_current_user, session):
    """``GET /api/users`` returns removed users too , which is correct behavior aimed
    at allowing users to be re-listed into the app and to keep track of history."""

    from models import User

    active_user = User(first_name="AU", last_name="AU", email="AU@test.example", timezone="UTC")
    removed_user = User(
        first_name="RU", last_name="RU", email="RU@test.example", timezone="UTC", removed=True
    )
    session.add(active_user)
    session.add(removed_user)
    session.commit()

    res = client.get("/api/users")
    assert res.status_code == 200
    rows = {u["email"]: u for u in res.json()}
    assert "AU@test.example" in rows
    assert "RU@test.example" in rows
    # The active row omits the ``removed`` field (response_model_exclude_none),
    # the removed row carries it as True so the UI can show the badge.
    assert rows["AU@test.example"].get("removed") in (None, False)
    assert rows["RU@test.example"]["removed"] is True


def test_restore_user_flips_removed_flag(client, stub_current_user, session):
    """``POST /api/users/{id}/restore`` flips ``removed`` back to false on
    a soft-deleted user. Verifies both the immediate POST response and a
    follow-up GET observe the same state."""

    from models import User

    removed_user = User(
        first_name="RU", last_name="RU", email="RU@test.example",
        timezone="UTC", removed=True,
    )
    session.add(removed_user)
    session.commit()

    res = client.post(f"/api/users/{removed_user.id}/restore")
    assert res.status_code == 200
    body = res.json()
    # Restored users no longer carry the removed flag (excluded as None).
    assert body.get("removed") in (None, False)

    # Confirm GET reflects the new state.
    after = client.get(f"/api/users/{removed_user.id}").json()
    assert after.get("removed") in (None, False)


def test_soft_delete_user_keeps_row(client, stub_current_user, session):
    """``DELETE /api/users/{id}`` keeps the user row, ``removed=True``
    is set, and a direct GET still resolves the user."""

    from models import User

    removed_user = User(first_name="RU", last_name="RU", email="RU@test.example", timezone="UTC")
    session.add(removed_user)
    session.commit()

    res = client.delete(f"/api/users/{removed_user.id}")
    assert res.status_code == 204

    # Direct GET still works (soft delete keeps the row).
    detail = client.get(f"/api/users/{removed_user.id}")
    assert detail.status_code == 200
    assert detail.json()["removed"] is True
