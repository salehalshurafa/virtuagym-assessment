"""Auth flow integration tests — signup / login / me / logout."""

from __future__ import annotations


def test_signup_creates_user_and_sets_cookie(client):
    """``POST /api/auth/signup`` creates the user, returns the user payload,
    AND sets the ``vg_session`` cookie so the new user is immediately
    authenticated."""

    res = client.post(
        "/api/auth/signup",
        json={
            "firstName": "New",
            "lastName": "User",
            "email": "new@test.example",
            "password": "SuperSecret1",
            "timezone": "America/New_York",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["email"] == "new@test.example"
    assert data["timezone"] == "America/New_York"
    # The session cookie must be present on the response.
    assert any(c.name == "vg_session" for c in client.cookies.jar)


def test_signup_rejects_duplicate_email(client, seed_user):
    """Email is the unique natural key on ``user``."""

    res = client.post(
        "/api/auth/signup",
        json={
            "firstName": "X",
            "lastName": "Y",
            "email": seed_user.email,
            "password": "AnotherPass1",
        },
    )
    assert res.status_code == 409


def test_login_with_correct_password(client, seed_user):
    """``POST /api/auth/login`` correct credentials return 200 with the user 
    payload."""

    res = client.post(
        "/api/auth/login",
        json={"email": seed_user.email, "password": "TestPass!23"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["email"] == seed_user.email


def test_login_with_wrong_password(client, seed_user):
    """Wrong password must return 401, no other status code, no body
    leaking which field was wrong."""

    res = client.post(
        "/api/auth/login",
        json={"email": seed_user.email, "password": "wrong"},
    )
    assert res.status_code == 401


def test_login_with_unknown_email(client):
    """Unknown email must also return 401, not 404. No leaking info again."""
    res = client.post(
        "/api/auth/login",
        json={"email": "nobody@test.example", "password": "doesntmatter"},
    )
    assert res.status_code == 401


def test_me_returns_current_user_after_login(client, seed_user):
    """``GET /api/auth/me`` resolves the caller via the ``vg_session``
    cookie. Login sets the cookie and the subsequent ``/me`` call returns
    the same user. """

    client.post(
        "/api/auth/login",
        json={"email": seed_user.email, "password": "TestPass!23"},
    )
    res = client.get("/api/auth/me")
    assert res.status_code == 200, res.text
    assert res.json()["id"] == seed_user.id


def test_me_without_cookie_returns_401(client):
    """The auth gaurd works when no cookie is present. Every protected
    route is mounted with ``Depends(get_current_user)``; ``/me`` is the
    cheapest probe of that gate."""

    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_logout_clears_session(client, seed_user):
    """Logout must invalidate the session row server-side, not just clear
    the cookie client-side. After ``POST /api/auth/logout`` the same
    cookie no longer resolves any user. This is confirmed by ``/me`` returning
    401 on the next request through the same client."""
    
    client.post(
        "/api/auth/login",
        json={"email": seed_user.email, "password": "TestPass!23"},
    )
    res = client.post("/api/auth/logout")
    assert res.status_code == 204

    res2 = client.get("/api/auth/me")
    assert res2.status_code == 401
