"""simplify exercise table — drop sets / reps / rest_seconds

Revision ID: f3a9b2c5e8d1
Revises: e7c4b1a9d2f5
Create Date: 2026-04-27 20:30:00.000000

The library Exercise carried defaults (sets / reps / rest_seconds) that
were never read at runtime — every per-day ExerciseAssignment overrides
them with its own values. Drop the dead columns so an Exercise template
is just name + image + video + instructions + usage_count.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9b2c5e8d1"
down_revision: Union[str, Sequence[str], None] = "e7c4b1a9d2f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("exercise", "rest_seconds")
    op.drop_column("exercise", "reps")
    op.drop_column("exercise", "sets")


def downgrade() -> None:
    op.add_column(
        "exercise",
        sa.Column("sets", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "exercise",
        sa.Column("reps", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "exercise",
        sa.Column(
            "rest_seconds", sa.Integer(), nullable=False, server_default="60"
        ),
    )
    # Drop the server defaults afterwards — the model defaults are owned
    # by Python-side `default=` values, not DB-level defaults.
    op.alter_column("exercise", "sets", server_default=None)
    op.alter_column("exercise", "reps", server_default=None)
    op.alter_column("exercise", "rest_seconds", server_default=None)
