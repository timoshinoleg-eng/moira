"""add timezone-aware push preferences and durable delivery journal

Revision ID: 0008_push_delivery_foundation
Revises: 0007_controlled_repair_telemetry
Create Date: 2026-08-19

The V2 preference fields start disabled. Existing legacy daily_push behaviour is
left untouched until the explicit opt-in UI and scheduler rollout are released.
The delivery table contains only scheduling state, never user-visible payloads.
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_push_delivery_foundation"
down_revision = "0007_controlled_repair_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("push_timezone", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("push_local_time", sa.String(length=5), nullable=True))
    op.add_column("users", sa.Column("next_push_at_utc", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "push_deliveries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("local_period", sa.String(length=16), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="planned"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "kind", "local_period", name="uq_push_delivery_user_kind_period"),
    )
    op.create_index("ix_push_deliveries_user_id", "push_deliveries", ["user_id"])
    op.create_index(
        "ix_push_deliveries_status_scheduled_at",
        "push_deliveries",
        ["status", "scheduled_at"],
    )
    op.create_index(
        "ix_push_deliveries_status_lease_until",
        "push_deliveries",
        ["status", "lease_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_push_deliveries_status_lease_until", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_status_scheduled_at", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_user_id", table_name="push_deliveries")
    op.drop_table("push_deliveries")
    op.drop_column("users", "next_push_at_utc")
    op.drop_column("users", "push_local_time")
    op.drop_column("users", "push_timezone")
    op.drop_column("users", "push_enabled")
