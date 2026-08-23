"""add optional voice-input state and reading source

Revision ID: 0004_voice_input
Revises: 0003_product_readiness
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_voice_input"
down_revision = "0003_product_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("voice_transcription_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "readings",
        sa.Column("input_mode", sa.String(length=16), nullable=False, server_default="text"),
    )


def downgrade() -> None:
    op.drop_column("readings", "input_mode")
    op.drop_column("users", "voice_transcription_consent")
