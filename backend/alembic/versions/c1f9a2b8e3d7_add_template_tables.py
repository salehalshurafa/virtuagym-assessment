"""add plan_template + weekly_split_template, drop is_template columns

Revision ID: c1f9a2b8e3d7
Revises: f3a9b2c5e8d1
Create Date: 2026-04-27 21:00:00.000000

Splits "the gallery" from "the live runtime tree". Two new tables hold
templates as JSON; live `plan` and `weekly_workout_plan` lose their
``is_template`` column entirely. Existing live rows are wiped via TRUNCATE
RESTART IDENTITY CASCADE — re-seed after upgrade.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c1f9a2b8e3d7"
down_revision: Union[str, Sequence[str], None] = "f3a9b2c5e8d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reference the existing Postgres ENUM rather than letting SQLAlchemy
    # auto-create it (the initial migration already created the type as a
    # side-effect of the `plan` table). `postgresql.ENUM(create_type=False)`
    # honours that, where `sa.Enum(create_type=False)` does not when
    # invoked inside `op.create_table`.
    duration_type = postgresql.ENUM(
        "days", "weeks", "months", "years", name="durationtype", create_type=False
    )

    # New gallery tables ------------------------------------------------------
    # `index=True` on the title / label columns produces
    # `ix_<table>_<col>` indexes automatically — no explicit create_index
    # follow-ups (those would collide with duplicate-name errors).
    op.create_table(
        "plan_template",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False, index=True),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("duration_type", duration_type, nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("workout_days_per_week", sa.Integer(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("weekly_plans", sa.JSON(), nullable=True),
        sa.Column("flat_days", sa.JSON(), nullable=True),
    )

    op.create_table(
        "weekly_split_template",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False, index=True),
        sa.Column("days", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )

    # Drop the no-longer-meaningful flag columns -----------------------------
    # Wipe live trees first since the schema is changing materially. Reseed
    # script is the source of truth post-migration.
    op.execute(
        "TRUNCATE TABLE "
        "exercise_assignment, plan_day, weekly_workout_plan_assignment, "
        "weekly_workout_plan, user_plan_assignment, plan "
        "RESTART IDENTITY CASCADE"
    )
    op.drop_column("plan", "is_template")
    op.drop_column("weekly_workout_plan", "is_template")


def downgrade() -> None:
    op.add_column(
        "weekly_workout_plan",
        sa.Column(
            "is_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("weekly_workout_plan", "is_template", server_default=None)
    op.add_column(
        "plan",
        sa.Column(
            "is_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("plan", "is_template", server_default=None)

    # Postgres drops the auto-created column indexes when the table goes.
    op.drop_table("weekly_split_template")
    op.drop_table("plan_template")
