"""Crawl sessions and richer page audit fields

Revision ID: 008_crawl_sessions
Revises: 007_onsite_live_fetch
Create Date: 2026-08-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_crawl_sessions"
down_revision: Union[str, None] = "007_onsite_live_fetch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("site_pages", sa.Column("discovery_source", sa.String(40), nullable=False, server_default="manual"))
    op.add_column("site_pages", sa.Column("is_in_sitemap", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("site_pages", sa.Column("meta_robots", sa.String(300), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("x_robots_tag", sa.String(300), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("site_pages", sa.Column("image_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("site_pages", sa.Column("images_missing_alt", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("site_pages", sa.Column("external_link_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "crawl_sessions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("origin", sa.String(500), nullable=False),
        sa.Column("mode", sa.String(40), nullable=False, server_default="site"),
        sa.Column("max_urls", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("status", sa.String(30), nullable=False, server_default="running"),
        sa.Column("discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("robots_blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("needs_js", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_sessions_tenant_id"), "crawl_sessions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_crawl_sessions_status"), "crawl_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_crawl_sessions_status"), table_name="crawl_sessions")
    op.drop_index(op.f("ix_crawl_sessions_tenant_id"), table_name="crawl_sessions")
    op.drop_table("crawl_sessions")
    op.drop_column("site_pages", "external_link_count")
    op.drop_column("site_pages", "images_missing_alt")
    op.drop_column("site_pages", "image_count")
    op.drop_column("site_pages", "word_count")
    op.drop_column("site_pages", "x_robots_tag")
    op.drop_column("site_pages", "meta_robots")
    op.drop_column("site_pages", "is_in_sitemap")
    op.drop_column("site_pages", "discovery_source")
