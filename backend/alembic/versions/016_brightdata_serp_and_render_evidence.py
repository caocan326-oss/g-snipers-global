"""brightdata serp and render evidence

Revision ID: 016_brightdata_serp_render
Revises: 015_geo_prompt_pack_and_type
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "016_brightdata_serp_render"
down_revision = "015_geo_prompt_pack_and_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("site_pages", sa.Column("fetch_mode", sa.String(length=40), nullable=False, server_default="http"))
    op.add_column("site_pages", sa.Column("render_status", sa.String(length=40), nullable=False, server_default="not_needed"))
    op.add_column("site_pages", sa.Column("render_final_url", sa.String(length=700), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("render_word_count", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "serp_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="brightdata"),
        sa.Column("keyword", sa.String(length=500), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("locale", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("device", sa.String(length=40), nullable=False, server_default="desktop"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="running"),
        sa.Column("own_domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("own_best_position", sa.Integer(), nullable=True),
        sa.Column("competitor_best_position", sa.Integer(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("third_party_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_serp_runs_tenant_id", "serp_runs", ["tenant_id"])
    op.create_index("ix_serp_runs_provider", "serp_runs", ["provider"])
    op.create_index("ix_serp_runs_keyword", "serp_runs", ["keyword"])
    op.create_index("ix_serp_runs_status", "serp_runs", ["status"])

    op.create_table(
        "serp_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("url", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column("result_type", sa.String(length=40), nullable=False, server_default="organic"),
        sa.Column("ownership", sa.String(length=40), nullable=False, server_default="third_party"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["serp_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_serp_results_tenant_id", "serp_results", ["tenant_id"])
    op.create_index("ix_serp_results_run_id", "serp_results", ["run_id"])
    op.create_index("ix_serp_results_domain", "serp_results", ["domain"])
    op.create_index("ix_serp_results_ownership", "serp_results", ["ownership"])


def downgrade() -> None:
    op.drop_index("ix_serp_results_ownership", table_name="serp_results")
    op.drop_index("ix_serp_results_domain", table_name="serp_results")
    op.drop_index("ix_serp_results_run_id", table_name="serp_results")
    op.drop_index("ix_serp_results_tenant_id", table_name="serp_results")
    op.drop_table("serp_results")
    op.drop_index("ix_serp_runs_status", table_name="serp_runs")
    op.drop_index("ix_serp_runs_keyword", table_name="serp_runs")
    op.drop_index("ix_serp_runs_provider", table_name="serp_runs")
    op.drop_index("ix_serp_runs_tenant_id", table_name="serp_runs")
    op.drop_table("serp_runs")
    op.drop_column("site_pages", "render_word_count")
    op.drop_column("site_pages", "render_final_url")
    op.drop_column("site_pages", "render_status")
    op.drop_column("site_pages", "fetch_mode")
