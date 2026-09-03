"""add one private note per reading

Revision ID: 0010_reading_notes
Revises: 0009_reading_provenance_feedback
Create Date: 2026-09-03

One row per reading (unique reading_id). Note text lives only here: it is
never copied to analytics, logs, or LLM prompts. Deleted explicitly before
readings in /delete_my_data so the FK to readings never blocks the cascade.
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_reading_notes"
down_revision = "0009_reading_provenance_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reading_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Unique index (not a table-level constraint) mirrors the model's column-level
    # unique=True, so `alembic check` stays clean on SQLite and Postgres alike.
    op.create_index("ix_reading_notes_user_id", "reading_notes", ["user_id"])
    op.create_index(
        "ix_reading_notes_reading_id", "reading_notes", ["reading_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_reading_notes_reading_id", table_name="reading_notes")
    op.drop_index("ix_reading_notes_user_id", table_name="reading_notes")
    op.drop_table("reading_notes")
