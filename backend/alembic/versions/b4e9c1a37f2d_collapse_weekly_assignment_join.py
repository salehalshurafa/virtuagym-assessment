"""collapse weekly_workout_plan_assignment into weekly_workout_plan

Revision ID: b4e9c1a37f2d
Revises: a8f2b6e4d903
Create Date: 2026-04-28 16:00:00.000000

The previous schema modeled the Plan ↔ WeeklyWorkoutPlan link as a
many-to-many via ``weekly_workout_plan_assignment``. In practice we
always materialize a fresh weekly per plan (no sharing), so the join
table just adds indirection. This migration:

1. Adds ``plan_id``, ``week_frequency``, ``order_index`` columns to
   ``weekly_workout_plan`` (so each weekly belongs to exactly one plan).
2. TRUNCATEs the live plan tree (plan → user_plan_assignment → ...) —
   the schema reshape is material enough that data preservation isn't
   worth a fragile backfill. Mirrors the precedent set by
   ``c1f9a2b8e3d7_add_template_tables.py``. Re-seed after upgrade.
3. Drops the ``weekly_workout_plan_assignment`` table.

After this, the only remaining many-to-many in the plan tree is
``user_plan_assignment`` (User ↔ Plan), which carries genuine per-link
metadata (start_date, end_date, status, assigned_by_*).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e9c1a37f2d"
down_revision: Union[str, Sequence[str], None] = "a8f2b6e4d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1 — wipe the live plan tree before reshaping. Templates
    # (plan_template / weekly_split_template) are JSON-stored and
    # untouched by this migration, so re-seeding fully reconstructs the
    # live data.
    op.execute(
        "TRUNCATE TABLE "
        "user_plan_assignment, "
        "weekly_workout_plan_assignment, "
        "weekly_workout_plan, "
        "plan_day, "
        "exercise_assignment, "
        "plan "
        "RESTART IDENTITY CASCADE"
    )

    # Step 2 — drop the join table outright. With the live tree
    # truncated there's nothing to backfill from.
    op.drop_table("weekly_workout_plan_assignment")

    # Step 3 — add the new columns onto weekly_workout_plan. Defaults
    # let alembic add them as NOT NULL without complaining about empty
    # rows; we then drop the server defaults so future inserts have to
    # supply the values explicitly (Python provides them via the model).
    op.add_column(
        "weekly_workout_plan",
        sa.Column(
            "plan_id",
            sa.String(),
            sa.ForeignKey("plan.id", ondelete="CASCADE"),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("weekly_workout_plan", "plan_id", server_default=None)
    op.create_index(
        "ix_weekly_workout_plan_plan_id",
        "weekly_workout_plan",
        ["plan_id"],
    )
    op.add_column(
        "weekly_workout_plan",
        sa.Column(
            "week_frequency",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.alter_column("weekly_workout_plan", "week_frequency", server_default=None)
    op.add_column(
        "weekly_workout_plan",
        sa.Column(
            "order_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column("weekly_workout_plan", "order_index", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_weekly_workout_plan_plan_id", table_name="weekly_workout_plan")
    op.drop_column("weekly_workout_plan", "order_index")
    op.drop_column("weekly_workout_plan", "week_frequency")
    op.drop_column("weekly_workout_plan", "plan_id")

    op.create_table(
        "weekly_workout_plan_assignment",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "weekly_plan_id",
            sa.String(),
            sa.ForeignKey("weekly_workout_plan.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.String(),
            sa.ForeignKey("plan.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column("week_frequency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
