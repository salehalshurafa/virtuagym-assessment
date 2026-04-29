"""Plan lifecycle integration — create → assign → list → modify → archive."""

from __future__ import annotations

from models import PlanTemplate


def basic_plan_payload(title: str = "Strength 4w") -> dict:
    return {
        "title": title,
        "duration": 4,
        "durationType": "weeks",
        "workoutDaysPerWeek": 3,
        "weeklyPlans": [
            {
                "label": "Push/Pull/Legs",
                "weekFrequency": 1,
                "orderIndex": 0,
                "days": [
                    {
                        "label": f"Day {i + 1}",
                        "isRest": i in (1, 3, 5, 6),
                        "orderIndex": i,
                        "exercises": (
                            []
                            if i in (1, 3, 5, 6)
                            else [
                                {
                                    "exerciseName": "Push-Up",
                                    "sets": 3,
                                    "reps": 10,
                                    "weightUnit": "kg",
                                    "restSeconds": 60,
                                    "orderIndex": 0,
                                }
                            ]
                        ),
                    }
                    for i in range(7)
                ],
            }
        ],
    }


def bulk_assign_one(client, plan_id: str, user_id: str) -> dict:
    """ Perform a bulk assign operation (usually is used to assing more than
    one user to a plan), but only to one user."""
    res = client.post(
        "/api/assignments/bulk",
        json={
            "planId": plan_id,
            "startDate": "2025-01-01",
            "userIds": [user_id],
            "forceReplaceUserIds": [],
        },
    )
    # Returns 200 (not 201) because the endpoint can succeed partially
    assert res.status_code == 200, res.text
    body = res.json()

    # the per-user success flags inside ``results`` carry the real outcome.
    assert all(r["success"] for r in body["results"]), body
    return body


def test_create_plan_then_assign_appears_on_active(
    client, stub_current_user, assignee
):
    """Create a live plan, assign one user, confirm ``/api/plans/active`` 
    returns the plan with the assignee embedded and a clean ``in-progress`` 
    status summary."""

    create = client.post("/api/plans", json=basic_plan_payload())
    assert create.status_code == 201, create.text
    plan_id = create.json()["id"]

    bulk_assign_one(client, plan_id, assignee.id)

    active = client.get("/api/plans/active")
    assert active.status_code == 200
    rows = active.json()
    row = next((r for r in rows if r["id"] == plan_id), None)
    assert row is not None, f"plan {plan_id} missing from /active: {rows}"
    assert row["statusSummary"] == "in-progress"
    assignee_ids = [a["id"] for a in row["assignees"]]
    assert assignee.id in assignee_ids


def test_patch_plan_emails_current_assignees(
    client, stub_current_user, assignee, fake_mailer
):
    """Modifying a live plan must fire ``send_plan_modified`` to every
    active assignee."""

    create = client.post("/api/plans", json=basic_plan_payload(title="Original Title"))
    plan_id = create.json()["id"]
    bulk_assign_one(client, plan_id, assignee.id)

    # Drop the assignment-fired email so we only inspect the modify event.
    fake_mailer.calls.clear()

    patch = client.patch(f"/api/plans/{plan_id}", json={"title": "Renamed"})
    assert patch.status_code == 200, patch.text
    assert patch.json()["title"] == "Renamed"

    modified = [c for c in fake_mailer.calls if c[0] == "plan_modified"]
    assert len(modified) == 1, f"expected 1 modify-email, got {fake_mailer.calls}"
    assert modified[0][1]["to"] == assignee.email
    assert modified[0][1]["title"] == "Renamed"


def test_delete_plan_archives_and_clears_from_active(
    client, stub_current_user, assignee, fake_mailer
):
    """``DELETE /api/plans/{id}`` sets ``archived=True``, fires ``send_plan_archived`` 
    to current assignees, and the plan disappears from ``/active``. The row stays 
    addressable by id so historical views still resolve the title."""

    create = client.post("/api/plans", json=basic_plan_payload(title="To Archive"))
    plan_id = create.json()["id"]
    bulk_assign_one(client, plan_id, assignee.id)
    fake_mailer.calls.clear()

    delete = client.delete(f"/api/plans/{plan_id}")
    assert delete.status_code == 204

    archived = [c for c in fake_mailer.calls if c[0] == "plan_archived"]
    assert len(archived) == 1
    assert archived[0][1]["to"] == assignee.email
    assert archived[0][1]["title"] == "To Archive"

    active = client.get("/api/plans/active").json()
    assert all(r["id"] != plan_id for r in active)

    detail = client.get(f"/api/plans/{plan_id}")
    assert detail.status_code == 200
    assert detail.json()["archived"] is True


def test_from_template_atomically_creates_plan_and_assigns(
    client, stub_current_user, session, assignee, fake_mailer
):
    """``POST /api/plans/from-template`` is meant to be atomic such that you
    instantiate a live plan from a template AND bulk-assign in one transaction.
    The frontend's "assign existing template (no edits)" flow depends on
    this. It's what closes the orphan-plan window where a plan would be
    created but the assignment failed.
    """

    payload = basic_plan_payload(title="Template Source")
    template = PlanTemplate(
        title=payload["title"],
        duration=payload["duration"],
        duration_type=payload["durationType"],
        workout_days_per_week=payload["workoutDaysPerWeek"],
        weekly_plans=payload["weeklyPlans"],
        flat_days=None,
        archived=False,
    )
    session.add(template)
    session.commit()
    session.refresh(template)

    res = client.post(
        "/api/plans/from-template",
        json={
            "templateId": template.id,
            "startDate": "2025-01-01",
            "userIds": [assignee.id],
            "forceReplaceUserIds": [],
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()

    plan_id = body["planId"]
    # Plan exists as a live row.
    detail = client.get(f"/api/plans/{plan_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Template Source"
    assert detail.json()["archived"] is False

    # Assignment landed.
    success = [r for r in body["results"] if r["success"]]
    assert {r["userId"] for r in success} == {assignee.id}

    # Email fired in the same transaction path.
    assert any(
        c[0] == "plan_assigned" and c[1]["to"] == assignee.email
        for c in fake_mailer.calls
    ), f"no plan_assigned email recorded: {fake_mailer.calls}"


def test_create_plan_validation_rejects_empty_workouts(client, stub_current_user):
    """Non-rest days must have at least one named exercise. The frontend
    validator catches this first, but the server-side check is the safety
    net."""
    
    payload = basic_plan_payload()
    for d in payload["weeklyPlans"][0]["days"]:
        d["exercises"] = []
        d["isRest"] = False
    res = client.post("/api/plans", json=payload)
    assert res.status_code == 400
