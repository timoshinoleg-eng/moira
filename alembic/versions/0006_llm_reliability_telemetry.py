"""persist safe LLM reliability telemetry

Revision ID: 0006_llm_reliability_telemetry
Revises: 0005_growth_attribution
Create Date: 2026-08-19

The added fields are deliberately bounded, categorical or generated identifiers.
They must never store a user question, prompt, raw completion, interpretation,
Telegram username or provider response body.
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_llm_reliability_telemetry"
down_revision = "0005_growth_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("llm_usage", sa.Column("provider", sa.String(length=128), nullable=True))
    op.add_column(
        "llm_usage",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "llm_usage",
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("llm_usage", sa.Column("error_category", sa.String(length=32), nullable=True))
    op.add_column("llm_usage", sa.Column("timeout_stage", sa.String(length=32), nullable=True))
    op.add_column("llm_usage", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_llm_usage_status_created_at",
        "llm_usage",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_llm_usage_model_created_at",
        "llm_usage",
        ["model", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_usage_model_created_at", table_name="llm_usage")
    op.drop_index("ix_llm_usage_status_created_at", table_name="llm_usage")
    op.drop_column("llm_usage", "request_id")
    op.drop_column("llm_usage", "timeout_stage")
    op.drop_column("llm_usage", "error_category")
    op.drop_column("llm_usage", "fallback_used")
    op.drop_column("llm_usage", "attempts")
    op.drop_column("llm_usage", "provider")
