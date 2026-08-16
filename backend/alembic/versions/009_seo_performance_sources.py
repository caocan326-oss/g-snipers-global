"""seo performance sources

Revision ID: 009_seo_performance_sources
Revises: 008_crawl_sessions
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "009_seo_performance_sources"
down_revision = "008_crawl_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_performance_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("imported_by", sa.String(length=36), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["imported_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seo_performance_imports_source"), "seo_performance_imports", ["source"], unique=False)
    op.create_index(op.f("ix_seo_performance_imports_tenant_id"), "seo_performance_imports", ["tenant_id"], unique=False)

    op.create_table(
        "seo_performance_rows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("import_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("date", sa.String(length=40), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=False),
        sa.Column("device", sa.String(length=80), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("page_url", sa.String(length=700), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("position", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["import_id"], ["seo_performance_imports.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seo_performance_rows_import_id"), "seo_performance_rows", ["import_id"], unique=False)
    op.create_index(op.f("ix_seo_performance_rows_page_url"), "seo_performance_rows", ["page_url"], unique=False)
    op.create_index(op.f("ix_seo_performance_rows_query"), "seo_performance_rows", ["query"], unique=False)
    op.create_index(op.f("ix_seo_performance_rows_source"), "seo_performance_rows", ["source"], unique=False)
    op.create_index(op.f("ix_seo_performance_rows_tenant_id"), "seo_performance_rows", ["tenant_id"], unique=False)

    op.create_table(
        "pagespeed_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.String(length=700), nullable=False),
        sa.Column("strategy", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("performance_score", sa.Integer(), nullable=True),
        sa.Column("seo_score", sa.Integer(), nullable=True),
        sa.Column("accessibility_score", sa.Integer(), nullable=True),
        sa.Column("best_practices_score", sa.Integer(), nullable=True),
        sa.Column("lcp_ms", sa.Integer(), nullable=True),
        sa.Column("inp_ms", sa.Integer(), nullable=True),
        sa.Column("cls", sa.Float(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("audited_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pagespeed_audits_status"), "pagespeed_audits", ["status"], unique=False)
    op.create_index(op.f("ix_pagespeed_audits_tenant_id"), "pagespeed_audits", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_pagespeed_audits_url"), "pagespeed_audits", ["url"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pagespeed_audits_url"), table_name="pagespeed_audits")
    op.drop_index(op.f("ix_pagespeed_audits_tenant_id"), table_name="pagespeed_audits")
    op.drop_index(op.f("ix_pagespeed_audits_status"), table_name="pagespeed_audits")
    op.drop_table("pagespeed_audits")
    op.drop_index(op.f("ix_seo_performance_rows_tenant_id"), table_name="seo_performance_rows")
    op.drop_index(op.f("ix_seo_performance_rows_source"), table_name="seo_performance_rows")
    op.drop_index(op.f("ix_seo_performance_rows_query"), table_name="seo_performance_rows")
    op.drop_index(op.f("ix_seo_performance_rows_page_url"), table_name="seo_performance_rows")
    op.drop_index(op.f("ix_seo_performance_rows_import_id"), table_name="seo_performance_rows")
    op.drop_table("seo_performance_rows")
    op.drop_index(op.f("ix_seo_performance_imports_tenant_id"), table_name="seo_performance_imports")
    op.drop_index(op.f("ix_seo_performance_imports_source"), table_name="seo_performance_imports")
    op.drop_table("seo_performance_imports")
