"""baseline: current production schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("free_readings", sa.Integer(), nullable=False),
        sa.Column("promo_readings", sa.Integer(), nullable=False),
        sa.Column("unlimited_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_promos", sa.Text(), nullable=False),
        sa.Column("birth_date", sa.String(length=10), nullable=True),
        sa.Column("daily_push", sa.Boolean(), nullable=False),
        sa.Column("last_push_date", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("spread", sa.String(length=32), nullable=False),
        sa.Column("cards_json", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_readings_user_id", "readings", ["user_id"])
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product", sa.String(length=32), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("charge_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_table(
        "promocodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promocodes_code", "promocodes", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_promocodes_code", table_name="promocodes")
    op.drop_table("promocodes")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_readings_user_id", table_name="readings")
    op.drop_table("readings")
    op.drop_table("users")
