"""add reading provenance columns and feedback table

Revision ID: 0009_reading_provenance_feedback
Revises: 0008_push_delivery_foundation
Create Date: 2026-09-03

All new columns are nullable so the migration never blocks writes on a live
table. Provenance links readings to llm_usage through generation_id, an opaque
correlation id with no user or prompt data.
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_reading_provenance_feedback"
down_revision = "0008_push_delivery_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("readings", sa.Column("generation_id", sa.String(length=64), nullable=True))
    op.create_index("ix_readings_generation_id", "readings", ["generation_id"])
    op.add_column("readings", sa.Column("result_json", sa.JSON(), nullable=True))
    op.add_column("readings", sa.Column("draw_engine_version", sa.String(length=16), nullable=True))
    op.add_column("readings", sa.Column("deck_version", sa.String(length=16), nullable=True))
    op.add_column("readings", sa.Column("spread_version", sa.String(length=16), nullable=True))

    op.add_column("llm_usage", sa.Column("generation_id", sa.String(length=64), nullable=True))
    op.create_index("ix_llm_usage_generation_id", "llm_usage", ["generation_id"])

    op.create_table(
        "reading_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("generation_id", sa.String(length=64), nullable=True),
        sa.Column("value", sa.String(length=16), nullable=False),
        sa.Column("checkpoint", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "reading_id", "checkpoint", name="uq_feedback_user_reading_checkpoint"),
    )
    op.create_index("ix_reading_feedback_user_id", "reading_feedback", ["user_id"])
    op.create_index("ix_reading_feedback_reading_id", "reading_feedback", ["reading_id"])
    op.create_index("ix_reading_feedback_generation_id", "reading_feedback", ["generation_id"])


def downgrade() -> None:
    op.drop_index("ix_reading_feedback_generation_id", table_name="reading_feedback")
    op.drop_index("ix_reading_feedback_reading_id", table_name="reading_feedback")
    op.drop_index("ix_reading_feedback_user_id", table_name="reading_feedback")
    op.drop_table("reading_feedback")
    op.drop_index("ix_llm_usage_generation_id", table_name="llm_usage")
    op.drop_column("llm_usage", "generation_id")
    op.drop_column("readings", "spread_version")
    op.drop_column("readings", "deck_version")
    op.drop_column("readings", "draw_engine_version")
    op.drop_column("readings", "result_json")
    op.drop_index("ix_readings_generation_id", table_name="readings")
    op.drop_column("readings", "generation_id")
