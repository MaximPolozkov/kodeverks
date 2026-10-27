"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
NOW = sa.text("now()")


def ts(name: str, *, nullable: bool = False, default: bool = True) -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        nullable=nullable,
        server_default=NOW if default else None,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        ts("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("author_external_id", sa.String(128)),
        sa.Column("author_name", sa.String(200)),
        sa.Column("profile_url", sa.String(500)),
        sa.Column("post_url", sa.String(500)),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Integer(), nullable=False),
        sa.Column("service_guess", sa.String(16)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("can_contact", sa.Boolean(), nullable=False),
        sa.Column("manual_mode", sa.Boolean(), nullable=False),
        sa.Column("public_token", sa.String(64), nullable=False),
        ts("link_sent_at", nullable=True, default=False),
        ts("created_at"),
        ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_leads"),
        sa.UniqueConstraint("source", "external_id", name="uq_leads_source_external_id"),
    )
    op.create_index("ix_leads_source", "leads", ["source"])
    op.create_index("ix_leads_author_external_id", "leads", ["author_external_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_public_token", "leads", ["public_token"], unique=True)
    op.create_index("ix_leads_created_at", "leads", ["created_at"])

    op.create_table(
        "bot_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_manual", sa.Boolean(), nullable=False),
        sa.Column("author_id", sa.Integer()),
        ts("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_bot_messages"),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name="fk_bot_messages_lead_id_leads", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_bot_messages_author_id_users", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_bot_messages_lead_id", "bot_messages", ["lead_id"])
    op.create_index("ix_bot_messages_created_at", "bot_messages", ["created_at"])

    op.create_table(
        "bot_stoplist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("author_external_id", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(200)),
        ts("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_bot_stoplist"),
        sa.UniqueConstraint(
            "source", "author_external_id", name="uq_bot_stoplist_source_author_external_id"
        ),
    )

    op.create_table(
        "bot_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("data", JSONB, nullable=False),
        ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_bot_settings"),
    )

    op.create_table(
        "bot_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        ts("started_at"),
        ts("finished_at", nullable=True, default=False),
        sa.Column("found_count", sa.Integer(), nullable=False),
        sa.Column("contacted_count", sa.Integer(), nullable=False),
        sa.Column("errors", sa.Integer(), nullable=False),
        sa.Column("log", JSONB, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_bot_runs"),
    )
    op.create_index("ix_bot_runs_started_at", "bot_runs", ["started_at"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("budget", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("service_type", sa.String(16)),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("utm_source", sa.String(100)),
        sa.Column("utm_medium", sa.String(100)),
        sa.Column("utm_campaign", sa.String(100)),
        sa.Column("utm_content", sa.String(100)),
        sa.Column("utm_term", sa.String(100)),
        sa.Column("lead_id", sa.Integer()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("ip_address", sa.String(64)),
        ts("created_at"),
        ts("updated_at"),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name="fk_orders_lead_id_leads", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_orders_email", "orders", ["email"])
    op.create_index("ix_orders_source", "orders", ["source"])
    op.create_index("ix_orders_lead_id", "orders", ["lead_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "order_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer()),
        sa.Column("text", sa.Text(), nullable=False),
        ts("created_at"),
        sa.PrimaryKeyConstraint("id", name="pk_order_comments"),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_order_comments_order_id_orders", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_order_comments_author_id_users", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_order_comments_order_id", "order_comments", ["order_id"])

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("old_status", sa.String(16)),
        sa.Column("new_status", sa.String(16), nullable=False),
        sa.Column("changed_by", sa.Integer()),
        ts("changed_at"),
        sa.PrimaryKeyConstraint("id", name="pk_order_status_history"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_order_status_history_order_id_orders",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name="fk_order_status_history_changed_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_order_status_history_order_id", "order_status_history", ["order_id"])


def downgrade() -> None:
    op.drop_table("order_status_history")
    op.drop_table("order_comments")
    op.drop_table("orders")
    op.drop_table("bot_runs")
    op.drop_table("bot_settings")
    op.drop_table("bot_stoplist")
    op.drop_table("bot_messages")
    op.drop_table("leads")
    op.drop_table("users")
