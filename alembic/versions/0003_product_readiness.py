"""persist privacy-safe sharing and response mode for a reading

Revision ID: 0003_product_readiness
Revises: 0002_growth
Create Date: 2026-08-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_product_readiness"
down_revision = "0002_growth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing readings are intentionally marked legacy: their historic
    # interpretation may not have a privacy-filtered share summary.
    op.add_column("readings", sa.Column("share_summary", sa.Text(), nullable=True))
    op.add_column(
        "readings",
        sa.Column("response_mode", sa.String(length=16), nullable=False, server_default="legacy"),
    )


def downgrade() -> None:
    op.drop_column("readings", "response_mode")
    op.drop_column("readings", "share_summary")
