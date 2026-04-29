"""add is_template to weekly_workout_plan

Revision ID: 7a3c9d1f4e8b
Revises: 4f8e9a2c1b7d
Create Date: 2026-04-27 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a3c9d1f4e8b'
down_revision: Union[str, Sequence[str], None] = '4f8e9a2c1b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_template flag. Existing rows (if any) all came from inline
    # plan-create flows that pre-date this distinction; they were created when
    # the gallery showed every WWP, so backfill them as templates so nothing
    # disappears from the picker. New inline rows default to False, and the
    # SaveTemplatesPanel flips ticked ones to True via PATCH.
    op.add_column(
        'weekly_workout_plan',
        sa.Column(
            'is_template',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column('weekly_workout_plan', 'is_template', server_default=sa.false())


def downgrade() -> None:
    op.drop_column('weekly_workout_plan', 'is_template')
