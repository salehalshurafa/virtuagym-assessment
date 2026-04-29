"""add auth columns and session table

Revision ID: 9c2e6f1d8b04
Revises: 7a3c9d1f4e8b
Create Date: 2026-04-27 18:00:00.000000

Adds the password_hash + timezone columns to user, and the session table
that holds DB-backed login sessions.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c2e6f1d8b04"
down_revision: Union[str, Sequence[str], None] = "7a3c9d1f4e8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User columns. password_hash is nullable so existing seeded users (no
    # password) don't break — they simply can't log in until an admin/seed
    # sets one. timezone defaults to UTC.
    op.add_column(
        "user",
        sa.Column("password_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "timezone",
            sa.String(),
            nullable=False,
            server_default=sa.text("'UTC'"),
        ),
    )
    op.alter_column("user", "timezone", server_default=None)

    # Sessions
    op.create_table(
        "session",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_session_token_hash", "session", ["token_hash"], unique=True
    )
    op.create_index("ix_session_user_id", "session", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_session_user_id", table_name="session")
    op.drop_index("ix_session_token_hash", table_name="session")
    op.drop_table("session")
    op.drop_column("user", "timezone")
    op.drop_column("user", "password_hash")
