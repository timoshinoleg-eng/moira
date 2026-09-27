"""add ritual streak counters and the daily activity table

Revision ID: 0011_ritual_streaks
Revises: 0010_reading_notes
Create Date: 2026-09-27

Backs the return loop in bot/services/streaks.py. The counters start at zero for
existing users, so nobody is credited with a streak they did not earn, and
ritual_days only ever stores a local date, an action count and a coarse kind —
never questions, interpretations or notes.
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_ritual_streaks"
down_revision = "0010_reading_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("streak_current", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("streak_longest", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("streak_freezes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("last_ritual_date", sa.String(length=10), nullable=True))

    op.create_table(
        "ritual_days",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("actions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_kind", sa.String(length=24), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "day", name="uq_ritual_day_user_day"),
    )
    op.create_index("ix_ritual_days_user_id", "ritual_days", ["user_id"])
    op.create_index("ix_ritual_days_day", "ritual_days", ["day"])


def downgrade() -> None:
    op.drop_index("ix_ritual_days_day", table_name="ritual_days")
    op.drop_index("ix_ritual_days_user_id", table_name="ritual_days")
    op.drop_table("ritual_days")
    op.drop_column("users", "last_ritual_date")
    op.drop_column("users", "streak_freezes")
    op.drop_column("users", "streak_longest")
    op.drop_column("users", "streak_current")
