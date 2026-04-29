"""add is_template to plan

Revision ID: 4f8e9a2c1b7d
Revises: 83b27cf3a645
Create Date: 2026-04-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f8e9a2c1b7d'
down_revision: Union[str, Sequence[str], None] = '83b27cf3a645'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_template flag. Existing rows are all templates by definition (they
    # were the only kind of plan before this change), so server_default=true
    # backfills them. We then drop the default so the application explicitly
    # sets this for new rows.
    op.add_column(
        'plan',
        sa.Column(
            'is_template',
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column('plan', 'is_template', server_default=None)


def downgrade() -> None:
    op.drop_column('plan', 'is_template')
