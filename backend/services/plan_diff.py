"""Compute human-readable diffs between two plan snapshots.

Used by the plan-modified email so the recipient can see what actually
changed in their plan.

The shape is the same `dict` produced by ``snapshot_plan`` so callers
take a snapshot before the PATCH, apply the changes, take another
snapshot after, then call ``compute_plan_diff(old, new)``.

Each diff entry is a small dict the mailer renders into HTML and text:

    {"kind": "field",        "label": "Title",   "old": "X", "new": "Y"}
    {"kind": "image",        "action": "added"}
    {"kind": "structure",    "summary": "Plan switched from weekly to flat layout"}
    {"kind": "day",          "where": "Week 1, Day 2 (Push)",
                              "changes": ["added Bench Press (3×10)", ...]}

Empty list means nothing meaningful changed.
"""

from __future__ import annotations

from typing import Any, Iterable

from models import Plan


def snapshot_plan(plan: Plan) -> dict[str, Any]:
    """Walk a live ``Plan`` into a plain dict suitable for diffing.

    Touches the same fields the mailer cares about. Skips ids — only
    user-visible content matters for the diff.
    """
    return {
        "title": plan.title,
        "duration": plan.duration,
        "duration_type": plan.duration_type.value
        if hasattr(plan.duration_type, "value")
        else str(plan.duration_type),
        "image_url": plan.image_url,
        "workout_days_per_week": plan.workout_days_per_week,
        "weekly_plans": [snapshot_week(wp) for wp in plan.weekly_plans],
        "flat_days": [snapshot_day(d) for d in plan.flat_days],
    }


def snapshot_week(wp) -> dict[str, Any]:
    return {
        "label": wp.label,
        "week_frequency": wp.week_frequency,
        "days": [snapshot_day(d) for d in wp.days],
    }


def snapshot_day(day) -> dict[str, Any]:
    return {
        "label": day.label,
        "is_rest": day.is_rest,
        "exercises": [snapshot_exercise(e) for e in day.exercises],
    }


def snapshot_exercise(ex) -> dict[str, Any]:
    return {
        "name": ex.exercise_name,
        "sets": ex.sets,
        "reps": ex.reps,
        "weight": ex.weight,
        "weight_unit": ex.weight_unit,
        "rest_seconds": ex.rest_seconds,
    }

def compute_plan_diff(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of diff entries describing what changed."""
    diffs: list[dict[str, Any]] = []

    if old["title"] != new["title"]:
        diffs.append({"kind": "field", "label": "Name", "old": old["title"], "new": new["title"]})

    if old["duration"] != new["duration"] or old["duration_type"] != new["duration_type"]:
        diffs.append(
            {
                "kind": "field",
                "label": "Duration",
                "old": format_duration(old["duration"], old["duration_type"]),
                "new": format_duration(new["duration"], new["duration_type"]),
            }
        )

    if old["workout_days_per_week"] != new["workout_days_per_week"]:
        diffs.append(
            {
                "kind": "field",
                "label": "Workout days per week",
                "old": format_optional_int(old["workout_days_per_week"]),
                "new": format_optional_int(new["workout_days_per_week"]),
            }
        )

    image_action = image_change(old["image_url"], new["image_url"])
    if image_action is not None:
        diffs.append({"kind": "image", "action": image_action})

    diffs.extend(diff_structure(old, new))

    return diffs


def diff_structure(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    old_weekly = bool(old.get("weekly_plans"))
    new_weekly = bool(new.get("weekly_plans"))
    old_flat = bool(old.get("flat_days"))
    new_flat = bool(new.get("flat_days"))

    if old_weekly != new_weekly or old_flat != new_flat:
        old_mode = "weekly" if old_weekly else ("flat" if old_flat else "empty")
        new_mode = "weekly" if new_weekly else ("flat" if new_flat else "empty")
        return [
            {
                "kind": "structure",
                "summary": f"Layout switched from {old_mode} to {new_mode}",
            }
        ]

    if new_weekly:
        return diff_weekly_lists(old["weekly_plans"], new["weekly_plans"])
    if new_flat:
        return diff_day_lists(old["flat_days"], new["flat_days"], where_prefix="")
    return []


def diff_weekly_lists(
    old_weeks: list[dict[str, Any]], new_weeks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    if len(old_weeks) != len(new_weeks):
        diffs.append(
            {
                "kind": "structure",
                "summary": (
                    f"Number of weekly patterns changed from {len(old_weeks)} to {len(new_weeks)}"
                ),
            }
        )

    for idx in range(max(len(old_weeks), len(new_weeks))):
        old_week = old_weeks[idx] if idx < len(old_weeks) else None
        new_week = new_weeks[idx] if idx < len(new_weeks) else None
        prefix = (new_week or old_week or {}).get("label") or f"Week pattern {idx + 1}"

        if old_week is None:
            diffs.append(
                {
                    "kind": "structure",
                    "summary": f"Added weekly pattern '{prefix}'",
                }
            )
            continue
        if new_week is None:
            diffs.append(
                {
                    "kind": "structure",
                    "summary": f"Removed weekly pattern '{old_week.get('label') or prefix}'",
                }
            )
            continue

        if old_week["label"] != new_week["label"]:
            diffs.append(
                {
                    "kind": "field",
                    "label": f"Weekly pattern {idx + 1} name",
                    "old": old_week["label"],
                    "new": new_week["label"],
                }
            )
        if old_week["week_frequency"] != new_week["week_frequency"]:
            diffs.append(
                {
                    "kind": "field",
                    "label": f"'{new_week['label']}' repeats for",
                    "old": format_weeks(old_week["week_frequency"]),
                    "new": format_weeks(new_week["week_frequency"]),
                }
            )
        diffs.extend(
            diff_day_lists(
                old_week["days"], new_week["days"], where_prefix=f"{new_week['label']} — "
            )
        )

    return diffs


def diff_day_lists(
    old_days: list[dict[str, Any]],
    new_days: list[dict[str, Any]],
    *,
    where_prefix: str,
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []
    if len(old_days) != len(new_days):
        diffs.append(
            {
                "kind": "structure",
                "summary": (
                    f"{where_prefix or 'Plan'}number of days changed from "
                    f"{len(old_days)} to {len(new_days)}"
                ).strip(),
            }
        )

    for idx in range(max(len(old_days), len(new_days))):
        old_day = old_days[idx] if idx < len(old_days) else None
        new_day = new_days[idx] if idx < len(new_days) else None
        position = idx + 1
        where = f"{where_prefix}Day {position}".strip()
        if new_day is not None and new_day["label"]:
            where = f"{where_prefix}Day {position} ({new_day['label']})"

        if old_day is None:
            diffs.append({"kind": "structure", "summary": f"Added {where}"})
            continue
        if new_day is None:
            removed_where = f"{where_prefix}Day {position}"
            if old_day["label"]:
                removed_where = f"{where_prefix}Day {position} ({old_day['label']})"
            diffs.append({"kind": "structure", "summary": f"Removed {removed_where}"})
            continue

        day_changes = diff_single_day(old_day, new_day)
        if day_changes:
            diffs.append({"kind": "day", "where": where, "changes": day_changes})

    return diffs


def diff_single_day(old_day: dict[str, Any], new_day: dict[str, Any]) -> list[str]:
    changes: list[str] = []

    if old_day["label"] != new_day["label"]:
        changes.append(f"renamed from '{old_day['label']}' to '{new_day['label']}'")

    if old_day["is_rest"] != new_day["is_rest"]:
        changes.append(
            "changed from a rest day to a workout day"
            if not new_day["is_rest"]
            else "changed from a workout day to a rest day"
        )
        # If toggled to rest, exercise diff is noisy — caller can stop here.
        if new_day["is_rest"]:
            return changes

    changes.extend(diff_exercise_lists(old_day["exercises"], new_day["exercises"]))
    return changes


def diff_exercise_lists(
    old_exs: list[dict[str, Any]], new_exs: list[dict[str, Any]]
) -> list[str]:
    """Compare exercise lists position-by-position.

    The frontend's editor preserves order, so positional comparison gives
    the most readable diff. Exercises that share a name across positions
    are still surfaced as edits (sets/reps/weight) rather than full
    add+remove pairs.
    """
    out: list[str] = []
    for idx in range(max(len(old_exs), len(new_exs))):
        old_ex = old_exs[idx] if idx < len(old_exs) else None
        new_ex = new_exs[idx] if idx < len(new_exs) else None

        if old_ex is None:
            out.append(f"added {describe_exercise(new_ex)}")
            continue
        if new_ex is None:
            out.append(f"removed {describe_exercise(old_ex)}")
            continue

        if old_ex["name"] != new_ex["name"]:
            out.append(
                f"replaced {describe_exercise(old_ex)} with {describe_exercise(new_ex)}"
            )
            continue

        edits = exercise_edits(old_ex, new_ex)
        if edits:
            out.append(f"updated {new_ex['name']} ({', '.join(edits)})")

    return out


def exercise_edits(old_ex: dict[str, Any], new_ex: dict[str, Any]) -> list[str]:
    edits: list[str] = []
    if old_ex["sets"] != new_ex["sets"] or old_ex["reps"] != new_ex["reps"]:
        edits.append(f"sets×reps {old_ex['sets']}×{old_ex['reps']} → {new_ex['sets']}×{new_ex['reps']}")
    if old_ex["weight"] != new_ex["weight"] or old_ex["weight_unit"] != new_ex["weight_unit"]:
        edits.append(
            f"weight {format_weight(old_ex['weight'], old_ex['weight_unit'])} → "
            f"{format_weight(new_ex['weight'], new_ex['weight_unit'])}"
        )
    if old_ex["rest_seconds"] != new_ex["rest_seconds"]:
        edits.append(f"rest {old_ex['rest_seconds']}s → {new_ex['rest_seconds']}s")
    return edits


def format_duration(value: int, unit: str) -> str:
    if value == 1:
        return f"1 {unit.rstrip('s')}"
    return f"{value} {unit}"


def format_weeks(value: int) -> str:
    return "1 week" if value == 1 else f"{value} weeks"


def format_optional_int(value: int | None) -> str:
    return "—" if value is None else str(value)


def format_weight(weight: float | None, unit: str) -> str:
    if weight is None:
        return "bodyweight"
    return f"{weight:g} {unit}"


def describe_exercise(ex: dict[str, Any]) -> str:
    return f"{ex['name']} ({ex['sets']}×{ex['reps']})"


def image_change(old_url: str | None, new_url: str | None) -> str | None:
    if old_url == new_url:
        return None
    if old_url is None and new_url is not None:
        return "added"
    if old_url is not None and new_url is None:
        return "removed"
    return "changed"
