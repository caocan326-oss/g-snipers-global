"""integration settings

Revision ID: 017_integration_settings
Revises: 016_brightdata_serp_render
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "017_integration_settings"
down_revision = "016_brightdata_serp_render"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_integration_settings_tenant_key"),
    )
    op.create_index("ix_integration_settings_tenant_id", "integration_settings", ["tenant_id"])
    op.create_index("ix_integration_settings_key", "integration_settings", ["key"])


def downgrade() -> None:
    op.drop_index("ix_integration_settings_key", table_name="integration_settings")
    op.drop_index("ix_integration_settings_tenant_id", table_name="integration_settings")
    op.drop_table("integration_settings")
