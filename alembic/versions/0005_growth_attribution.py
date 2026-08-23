"""persist share-caption attribution for referred users

Revision ID: 0005_growth_attribution
Revises: 0004_voice_input
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_growth_attribution"
down_revision = "0004_voice_input"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("referral_variant", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "referral_variant")
