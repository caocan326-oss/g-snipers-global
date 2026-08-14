"""Onsite live fetch: site origin + observation snapshot fields

Revision ID: 007_onsite_live_fetch
Revises: 006_ai_engine
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_onsite_live_fetch"
down_revision: Union[str, None] = "006_ai_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("site_origin", sa.String(500), nullable=False, server_default=""))
    op.alter_column("site_pages", "meta_title", existing_type=sa.String(200), type_=sa.Text(), existing_nullable=False)
    op.alter_column(
        "site_pages", "meta_description", existing_type=sa.String(400), type_=sa.Text(), existing_nullable=False
    )
    op.alter_column("site_pages", "canonical", existing_type=sa.String(500), type_=sa.Text(), existing_nullable=False)
    op.alter_column(
        "site_pages", "crawl_status", existing_type=sa.String(20), type_=sa.String(32), existing_nullable=False
    )
    op.add_column("site_pages", sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("site_pages", sa.Column("final_url", sa.String(500), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("http_status", sa.Integer(), nullable=True))
    op.add_column("site_pages", sa.Column("needs_js", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("site_pages", sa.Column("html_lang", sa.String(32), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("hreflang", sa.Text(), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("viewport", sa.String(300), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("json_ld_types", sa.String(400), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("crawl_error", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("site_pages", "crawl_error")
    op.drop_column("site_pages", "json_ld_types")
    op.drop_column("site_pages", "viewport")
    op.drop_column("site_pages", "hreflang")
    op.drop_column("site_pages", "html_lang")
    op.drop_column("site_pages", "needs_js")
    op.drop_column("site_pages", "http_status")
    op.drop_column("site_pages", "final_url")
    op.drop_column("site_pages", "fetched_at")
    op.alter_column(
        "site_pages", "crawl_status", existing_type=sa.String(32), type_=sa.String(20), existing_nullable=False
    )
    op.alter_column("site_pages", "canonical", existing_type=sa.Text(), type_=sa.String(500), existing_nullable=False)
    op.alter_column(
        "site_pages", "meta_description", existing_type=sa.Text(), type_=sa.String(400), existing_nullable=False
    )
    op.alter_column("site_pages", "meta_title", existing_type=sa.Text(), type_=sa.String(200), existing_nullable=False)
    op.drop_column("tenants", "site_origin")
