"""add assigned_by_name + assigned_by_email to user_plan_assignment

Revision ID: a8f2b6e4d903
Revises: d4e7f1c08b29
Create Date: 2026-04-28 13:00:00.000000

Records who assigned each plan to the user. Name + email snapshot rather
than a FK so the attribution survives the assigning admin being
soft-deleted or renamed. Both columns are nullable — historical rows
created before this migration won't have a value, and the UI handles that
gracefully.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f2b6e4d903"
down_revision: Union[str, Sequence[str], None] = "d4e7f1c08b29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_plan_assignment",
        sa.Column("assigned_by_name", sa.String(), nullable=True),
    )
    op.add_column(
        "user_plan_assignment",
        sa.Column("assigned_by_email", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_plan_assignment", "assigned_by_email")
    op.drop_column("user_plan_assignment", "assigned_by_name")
