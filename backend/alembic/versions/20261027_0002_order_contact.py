"""order contact channel and VK notification

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("contact_channel", sa.String(16), nullable=False, server_default="email"),
    )
    op.add_column("orders", sa.Column("contact_value", sa.String(200)))
    op.add_column("orders", sa.Column("vk_notified_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("orders", "vk_notified_at")
    op.drop_column("orders", "contact_value")
    op.drop_column("orders", "contact_channel")
