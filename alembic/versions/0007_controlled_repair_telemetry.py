"""persist controlled repair aggregate telemetry

Revision ID: 0007_controlled_repair_telemetry
Revises: 0006_llm_reliability_telemetry
Create Date: 2026-08-19

Only a boolean aggregate is persisted. Repair prompts, user questions, recent
memory and raw provider completions must never be written to this table.
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_controlled_repair_telemetry"
down_revision = "0006_llm_reliability_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_usage",
        sa.Column("repair_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("llm_usage", "repair_used")
