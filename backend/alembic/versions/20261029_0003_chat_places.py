"""chat places for lead discovery

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("url", sa.String(500)),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("found_count", sa.Integer(), nullable=False),
        sa.Column("bot_added", sa.Boolean(), nullable=False),
        sa.Column("watch", sa.Boolean(), nullable=False),
        sa.Column("hidden", sa.Boolean(), nullable=False),
        sa.Column("last_found_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chat_places"),
    )
    op.create_index("ix_chat_places_key", "chat_places", ["key"], unique=True)


def downgrade() -> None:
    op.drop_table("chat_places")
