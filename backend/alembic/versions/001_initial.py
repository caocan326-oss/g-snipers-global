"""initial insight + seo workbench schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="account_manager"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "markets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(40), nullable=False),
        sa.Column("country_code", sa.String(8), nullable=False),
        sa.Column("primary_locale", sa.String(16), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="watching"),
        sa.Column("opportunity_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_markets_tenant_id", "markets", ["tenant_id"])

    op.create_table(
        "competitors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("website", sa.String(500)),
        sa.Column("positioning", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_competitors_tenant_id", "competitors", ["tenant_id"])
    op.create_index("ix_competitors_market_id", "competitors", ["market_id"])

    op.create_table(
        "demand_signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("theme", sa.String(300), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("intent", sa.String(40), nullable=False, server_default="informational"),
        sa.Column("source", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_demand_signals_tenant_id", "demand_signals", ["tenant_id"])
    op.create_index("ix_demand_signals_market_id", "demand_signals", ["market_id"])

    op.create_table(
        "insight_briefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("opportunities", sa.Text(), nullable=False, server_default=""),
        sa.Column("risks", sa.Text(), nullable=False, server_default=""),
        sa.Column("recommended_actions", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("market_id", name="uq_insight_briefs_market"),
    )
    op.create_index("ix_insight_briefs_tenant_id", "insight_briefs", ["tenant_id"])
    op.create_index("ix_insight_briefs_market_id", "insight_briefs", ["market_id"])

    op.create_table(
        "seo_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id")),
        sa.Column("demand_signal_id", sa.String(36), sa.ForeignKey("demand_signals.id")),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("target_keyword", sa.String(300), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="idea"),
        sa.Column("outline", sa.Text(), nullable=False, server_default=""),
        sa.Column("draft_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta_title", sa.String(200), nullable=False, server_default=""),
        sa.Column("meta_description", sa.String(400), nullable=False, server_default=""),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_seo_pages_tenant_id", "seo_pages", ["tenant_id"])
    op.create_index("ix_seo_pages_market_id", "seo_pages", ["market_id"])
    op.create_index("ix_seo_pages_status", "seo_pages", ["status"])

    op.create_table(
        "work_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("type", sa.String(40), nullable=False, server_default="other"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("assignee_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("seo_page_id", sa.String(36), sa.ForeignKey("seo_pages.id")),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id")),
        sa.Column("acceptance_criteria", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_work_orders_tenant_id", "work_orders", ["tenant_id"])
    op.create_index("ix_work_orders_status", "work_orders", ["status"])

    op.create_table(
        "inquiries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("contact", sa.String(300), nullable=False),
        sa.Column("quality", sa.String(20), nullable=False, server_default="unreviewed"),
        sa.Column("related_seo_page_id", sa.String(36), sa.ForeignKey("seo_pages.id")),
        sa.Column("related_work_order_id", sa.String(36), sa.ForeignKey("work_orders.id")),
        sa.Column("related_market_id", sa.String(36), sa.ForeignKey("markets.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_inquiries_tenant_id", "inquiries", ["tenant_id"])

    op.create_table(
        "publish_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("seo_page_id", sa.String(36), sa.ForeignKey("seo_pages.id"), nullable=False),
        sa.Column("confirmed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_publish_confirmations_tenant_id", "publish_confirmations", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("publish_confirmations")
    op.drop_table("inquiries")
    op.drop_table("work_orders")
    op.drop_table("seo_pages")
    op.drop_table("insight_briefs")
    op.drop_table("demand_signals")
    op.drop_table("competitors")
    op.drop_table("markets")
    op.drop_table("users")
    op.drop_table("tenants")
