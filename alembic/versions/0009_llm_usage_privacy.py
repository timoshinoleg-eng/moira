"""remove user identity from LLM reliability telemetry

Revision ID: 0009_llm_usage_privacy
Revises: 0008_push_delivery_foundation
Create Date: 2026-08-20

LLM reliability telemetry is aggregate operational evidence. It must never
contain a Telegram user ID. Existing aggregate rows are preserved while the
identity column and its index are removed.
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_llm_usage_privacy"
down_revision = "0008_push_delivery_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("llm_usage") as batch:
        batch.drop_index("ix_llm_usage_user_id")
        batch.drop_column("user_id")


def downgrade() -> None:
    # Identity values cannot and must not be reconstructed. A downgrade only
    # restores a nullable compatibility column for the older application.
    with op.batch_alter_table("llm_usage") as batch:
        batch.add_column(sa.Column("user_id", sa.BigInteger(), nullable=True))
        batch.create_index("ix_llm_usage_user_id", ["user_id"], unique=False)
