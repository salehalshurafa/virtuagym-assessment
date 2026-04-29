"""add gender and phone to user

Revision ID: e7c4b1a9d2f5
Revises: b5d3e9af72c6
Create Date: 2026-04-27 20:00:00.000000

Both columns nullable — existing users have NULL on both. Gender uses a
Postgres ENUM with three values; phone is a free-text string.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7c4b1a9d2f5"
down_revision: Union[str, Sequence[str], None] = "b5d3e9af72c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    gender_enum = sa.Enum(
        "male",
        "female",
        "other",
        name="gender",
        create_type=False,
    )
    # Create the enum type explicitly so we can guard with IF NOT EXISTS via
    # the bind. SQLAlchemy will otherwise auto-create it the first time the
    # column references it.
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE gender AS ENUM ('male', 'female', 'other'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    op.add_column(
        "user",
        sa.Column("gender", gender_enum, nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("phone_number", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "phone_number")
    op.drop_column("user", "gender")
    op.execute("DROP TYPE IF EXISTS gender")
