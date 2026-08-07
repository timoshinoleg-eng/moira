"""payment ledger + growth tables (referrals, favorites, llm_usage, events)

Revision ID: 0002_growth
Revises: 0001_baseline
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0002_growth"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE payments SET charge_id = 'legacy_' || id WHERE charge_id IS NULL OR charge_id = ''")
    with op.batch_alter_table("payments") as batch:
        batch.alter_column("charge_id", existing_type=sa.String(length=128), nullable=False)
        batch.create_unique_constraint("uq_payments_charge_id", ["charge_id"])
    op.add_column("payments", sa.Column("status", sa.String(length=16), nullable=False, server_default="paid"))

    op.add_column("users", sa.Column("referred_by", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("last_mirror_week", sa.String(length=8), nullable=True))

    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("promo_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "promo_id", name="uq_promo_redemption"),
    )
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])

    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("referrer_id", sa.BigInteger(), nullable=False),
        sa.Column("referred_id", sa.BigInteger(), nullable=False),
        sa.Column("rewarded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("referred_id", name="uq_referral_referred"),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"])

    op.create_table(
        "reading_favorites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "reading_id", name="uq_favorite"),
    )
    op.create_index("ix_reading_favorites_user_id", "reading_favorites", ["user_id"])

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("spread", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_user_id", "llm_usage", ["user_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("distinct_id", sa.String(length=32), nullable=False),
        sa.Column("props_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_name", "events", ["name"])
    op.create_index("ix_events_distinct_id", "events", ["distinct_id"])


def downgrade() -> None:
    op.drop_index("ix_events_distinct_id", table_name="events")
    op.drop_index("ix_events_name", table_name="events")
    op.drop_table("events")
    op.drop_index("ix_llm_usage_user_id", table_name="llm_usage")
    op.drop_table("llm_usage")
    op.drop_index("ix_reading_favorites_user_id", table_name="reading_favorites")
    op.drop_table("reading_favorites")
    op.drop_index("ix_referrals_referrer_id", table_name="referrals")
    op.drop_table("referrals")
    op.drop_index("ix_promo_redemptions_user_id", table_name="promo_redemptions")
    op.drop_table("promo_redemptions")
    op.drop_column("users", "last_mirror_week")
    op.drop_column("users", "referred_by")
    op.drop_column("payments", "status")
    with op.batch_alter_table("payments") as batch:
        batch.drop_constraint("uq_payments_charge_id", type_="unique")
        batch.alter_column("charge_id", existing_type=sa.String(length=128), nullable=True)
