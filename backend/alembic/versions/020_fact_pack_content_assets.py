"""fact pack and content assets

Revision ID: 020_fact_pack_content_assets
Revises: 019_execution_platform_accounts
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "020_fact_pack_content_assets"
down_revision = "019_execution_platform_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fact_packs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default="Default Fact Pack"),
        sa.Column("legal_name", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("brand_names", sa.Text(), nullable=False, server_default=""),
        sa.Column("website", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("product_categories_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("certifications", sa.Text(), nullable=False, server_default=""),
        sa.Column("key_specs", sa.Text(), nullable=False, server_default=""),
        sa.Column("banned_claims", sa.Text(), nullable=False, server_default=""),
        sa.Column("contact_public", sa.Text(), nullable=False, server_default=""),
        sa.Column("approved_boilerplate_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fact_packs_tenant_id", "fact_packs", ["tenant_id"])
    op.create_index("ix_fact_packs_status", "fact_packs", ["status"])

    op.create_table(
        "content_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("fact_pack_id", sa.String(length=36), nullable=True),
        sa.Column("asset_type", sa.String(length=40), nullable=False, server_default="company_blurb"),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("locale", sa.String(length=20), nullable=False, server_default="en"),
        sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        sa.Column("entities", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("ai_review_status", sa.String(length=20), nullable=False, server_default="untested"),
        sa.Column("ai_review", sa.Text(), nullable=False, server_default=""),
        sa.Column("human_review_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["fact_pack_id"], ["fact_packs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_assets_tenant_id", "content_assets", ["tenant_id"])
    op.create_index("ix_content_assets_fact_pack_id", "content_assets", ["fact_pack_id"])
    op.create_index("ix_content_assets_asset_type", "content_assets", ["asset_type"])
    op.create_index("ix_content_assets_status", "content_assets", ["status"])

    op.add_column("distribution_jobs", sa.Column("content_asset_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_distribution_jobs_content_asset_id", "distribution_jobs", "content_assets", ["content_asset_id"], ["id"])
    op.create_index("ix_distribution_jobs_content_asset_id", "distribution_jobs", ["content_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_distribution_jobs_content_asset_id", table_name="distribution_jobs")
    op.drop_constraint("fk_distribution_jobs_content_asset_id", "distribution_jobs", type_="foreignkey")
    op.drop_column("distribution_jobs", "content_asset_id")
    op.drop_index("ix_content_assets_status", table_name="content_assets")
    op.drop_index("ix_content_assets_asset_type", table_name="content_assets")
    op.drop_index("ix_content_assets_fact_pack_id", table_name="content_assets")
    op.drop_index("ix_content_assets_tenant_id", table_name="content_assets")
    op.drop_table("content_assets")
    op.drop_index("ix_fact_packs_status", table_name="fact_packs")
    op.drop_index("ix_fact_packs_tenant_id", table_name="fact_packs")
    op.drop_table("fact_packs")
