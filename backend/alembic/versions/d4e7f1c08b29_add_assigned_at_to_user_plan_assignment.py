"""add assigned_at to user_plan_assignment

Revision ID: d4e7f1c08b29
Revises: c1f9a2b8e3d7
Create Date: 2026-04-28 12:00:00.000000

Adds an ``assigned_at`` timestamp so we can order a user's assignments
deterministically when two share the same ``start_date`` (e.g. a plan
created and another cancelled on the same day). Lifecycle helpers
``resume()`` and ``restart()`` bump this column so a revived assignment
becomes the user's "latest" again.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e7f1c08b29"
down_revision: Union[str, Sequence[str], None] = "c1f9a2b8e3d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as NOT NULL with a server-default of NOW() so existing rows get a
    # non-null backfill in one shot. Then drop the server default — Python
    # supplies the value on every new row from now on.
    op.add_column(
        "user_plan_assignment",
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.alter_column("user_plan_assignment", "assigned_at", server_default=None)


def downgrade() -> None:
    op.drop_column("user_plan_assignment", "assigned_at")
