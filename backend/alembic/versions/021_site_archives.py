"""site archives

Revision ID: 021_site_archives
Revises: 020_fact_pack_content_assets
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "021_site_archives"
down_revision = "020_fact_pack_content_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_archives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("site_origin", sa.String(length=500), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("counts_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("archived_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_site_archives_tenant_id", "site_archives", ["tenant_id"])
    op.create_index("ix_site_archives_site_origin", "site_archives", ["site_origin"])
    op.create_index("ix_site_archives_archived_at", "site_archives", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_site_archives_archived_at", table_name="site_archives")
    op.drop_index("ix_site_archives_site_origin", table_name="site_archives")
    op.drop_index("ix_site_archives_tenant_id", table_name="site_archives")
    op.drop_table("site_archives")
