"""per-tenant daily usage caps

Revision ID: 022_usage_quotas
Revises: 021_site_archives
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "022_usage_quotas"
down_revision = "021_site_archives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_quotas",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("meter", sa.String(length=40), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_quotas_tenant_id", "usage_quotas", ["tenant_id"])
    op.create_index("ix_usage_quotas_meter", "usage_quotas", ["meter"])
    op.create_unique_constraint("uq_usage_quotas_tenant_meter", "usage_quotas", ["tenant_id", "meter"])

    op.create_table(
        "usage_daily",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("meter", sa.String(length=40), nullable=False),
        sa.Column("used_on", sa.String(length=10), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_daily_tenant_id", "usage_daily", ["tenant_id"])
    op.create_index("ix_usage_daily_meter", "usage_daily", ["meter"])
    op.create_index("ix_usage_daily_used_on", "usage_daily", ["used_on"])
    op.create_unique_constraint("uq_usage_daily_tenant_meter_day", "usage_daily", ["tenant_id", "meter", "used_on"])


def downgrade() -> None:
    op.drop_table("usage_daily")
    op.drop_table("usage_quotas")
