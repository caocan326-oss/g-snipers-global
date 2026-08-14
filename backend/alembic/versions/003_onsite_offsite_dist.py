"""onsite, offsite, distribution

Revision ID: 003_onsite_offsite_dist
Revises: 002_geo
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_onsite_offsite_dist"
down_revision: Union[str, None] = "002_geo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "site_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id")),
        sa.Column("seo_page_id", sa.String(36), sa.ForeignKey("seo_pages.id")),
        sa.Column("path", sa.String(400), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("meta_title", sa.String(200), nullable=False, server_default=""),
        sa.Column("meta_description", sa.String(400), nullable=False, server_default=""),
        sa.Column("meta_keywords", sa.String(300), nullable=False, server_default=""),
        sa.Column("headings", sa.Text(), nullable=False, server_default=""),
        sa.Column("internal_links", sa.Text(), nullable=False, server_default=""),
        sa.Column("structured_data", sa.Text(), nullable=False, server_default=""),
        sa.Column("index_status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("crawl_status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_site_pages_tenant_id", "site_pages", ["tenant_id"])
    op.create_index("ix_site_pages_market_id", "site_pages", ["market_id"])

    op.create_table(
        "onsite_issues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("page_id", sa.String(36), sa.ForeignKey("site_pages.id"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_change", sa.Text(), nullable=False, server_default=""),
        sa.Column("risk", sa.String(10), nullable=False, server_default="low"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("metric_status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_onsite_issues_tenant_id", "onsite_issues", ["tenant_id"])
    op.create_index("ix_onsite_issues_page_id", "onsite_issues", ["page_id"])
    op.create_index("ix_onsite_issues_status", "onsite_issues", ["status"])

    op.create_table(
        "backlink_gaps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id")),
        sa.Column("competitor_name", sa.String(200), nullable=False),
        sa.Column("referring_domain", sa.String(300), nullable=False),
        sa.Column("competitor_url", sa.String(500)),
        sa.Column("our_presence", sa.String(20), nullable=False, server_default="none"),
        sa.Column("domain_metric", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("status", sa.String(20), nullable=False, server_default="identified"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_backlink_gaps_tenant_id", "backlink_gaps", ["tenant_id"])
    op.create_index("ix_backlink_gaps_status", "backlink_gaps", ["status"])

    op.create_table(
        "outreach_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("gap_id", sa.String(36), sa.ForeignKey("backlink_gaps.id"), nullable=False),
        sa.Column("contact", sa.String(300), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False, server_default="email"),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outreach_items_tenant_id", "outreach_items", ["tenant_id"])
    op.create_index("ix_outreach_items_gap_id", "outreach_items", ["gap_id"])

    op.create_table(
        "distribution_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("target_url", sa.String(500), nullable=False),
        sa.Column("provider_key", sa.String(40), nullable=False),
        sa.Column("payload_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("last_result", sa.String(40), nullable=False, server_default="未发送"),
        sa.Column("last_detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_distribution_jobs_tenant_id", "distribution_jobs", ["tenant_id"])
    op.create_index("ix_distribution_jobs_status", "distribution_jobs", ["status"])

    op.create_table(
        "distribution_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("distribution_jobs.id"), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result", sa.String(40), nullable=False, server_default="未发送"),
        sa.Column("detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_distribution_attempts_tenant_id", "distribution_attempts", ["tenant_id"])
    op.create_index("ix_distribution_attempts_job_id", "distribution_attempts", ["job_id"])


def downgrade() -> None:
    op.drop_table("distribution_attempts")
    op.drop_table("distribution_jobs")
    op.drop_table("outreach_items")
    op.drop_table("backlink_gaps")
    op.drop_table("onsite_issues")
    op.drop_table("site_pages")
