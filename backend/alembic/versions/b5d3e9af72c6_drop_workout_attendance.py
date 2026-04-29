"""drop workout_attendance table and AttendanceStatus enum

Revision ID: b5d3e9af72c6
Revises: 9c2e6f1d8b04
Create Date: 2026-04-27 19:30:00.000000

The attendance feature was scope-creep relative to the brief. Dropping the
table, the enum type, and the derived "last workout" columns the user
serializer used to expose.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5d3e9af72c6"
down_revision: Union[str, Sequence[str], None] = "9c2e6f1d8b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Indexes are dropped automatically with the table on Postgres, but be
    # explicit so a SQLite test DB doesn't choke on the same upgrade path.
    op.drop_table("workout_attendance")
    # The Python Enum class is gone, so the Postgres ENUM type it created
    # is now unreferenced. Drop it so a future re-add doesn't collide.
    op.execute("DROP TYPE IF EXISTS attendancestatus")


def downgrade() -> None:
    # Recreate enough to round-trip a downgrade. Doesn't restore data.
    op.execute(
        "CREATE TYPE attendancestatus AS ENUM ('attended', 'absent', 'injured', 'sick')"
    )
    op.create_table(
        "workout_attendance",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_plan_assignment_id",
            sa.String(),
            sa.ForeignKey("user_plan_assignment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_day_id",
            sa.String(),
            sa.ForeignKey("plan_day.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "attended",
                "absent",
                "injured",
                "sick",
                name="attendancestatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "user_plan_assignment_id", "date", name="uq_attendance_per_day"
        ),
    )
    op.create_index(
        "ix_workout_attendance_user_plan_assignment_id",
        "workout_attendance",
        ["user_plan_assignment_id"],
    )
    op.create_index(
        "ix_workout_attendance_plan_day_id",
        "workout_attendance",
        ["plan_day_id"],
    )
