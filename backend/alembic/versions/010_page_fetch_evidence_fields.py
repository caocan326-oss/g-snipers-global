"""page fetch evidence fields

Revision ID: 010_page_fetch_evidence_fields
Revises: 009_seo_performance_sources
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "010_page_fetch_evidence_fields"
down_revision = "009_seo_performance_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_pages", sa.Column("content_type", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("ttfb_ms", sa.Integer(), nullable=True))
    op.add_column("site_pages", sa.Column("redirect_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("site_pages", sa.Column("html_bytes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("site_pages", sa.Column("body_hash", sa.String(length=64), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("site_pages", "body_hash")
    op.drop_column("site_pages", "html_bytes")
    op.drop_column("site_pages", "redirect_count")
    op.drop_column("site_pages", "ttfb_ms")
    op.drop_column("site_pages", "content_type")
