"""execution fields and platform accounts

Revision ID: 019_execution_platform_accounts
Revises: 018_offsite_issue_execution
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "019_execution_platform_accounts"
down_revision = "018_offsite_issue_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("onsite_issues", "geo_tickets"):
        op.add_column(table, sa.Column("priority", sa.String(length=10), nullable=False, server_default="P2"))
        op.add_column(table, sa.Column("owner_hint", sa.String(length=120), nullable=False, server_default=""))
        op.add_column(table, sa.Column("recommended_action", sa.Text(), nullable=False, server_default=""))
        op.add_column(table, sa.Column("retest_method", sa.Text(), nullable=False, server_default=""))
        op.add_column(table, sa.Column("retest_result", sa.Text(), nullable=False, server_default=""))
        op.add_column(table, sa.Column("blocked_reason", sa.Text(), nullable=False, server_default=""))
        op.add_column(table, sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("onsite_issues", sa.Column("acceptance_criteria", sa.Text(), nullable=False, server_default=""))
    op.add_column("onsite_issues", sa.Column("result_url", sa.String(length=500), nullable=False, server_default=""))

    op.create_table(
        "source_platforms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("platform_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="directory"),
        sa.Column("regions", sa.Text(), nullable=False, server_default=""),
        sa.Column("industry_tags", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("listing_model", sa.String(length=40), nullable=False, server_default="directory_profile"),
        sa.Column("submission_mode", sa.String(length=40), nullable=False, server_default="manual_login"),
        sa.Column("has_official_api", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_platforms_tenant_id", "source_platforms", ["tenant_id"])
    op.create_index("ix_source_platforms_platform_key", "source_platforms", ["platform_key"])
    op.create_index("ix_source_platforms_status", "source_platforms", ["status"])

    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("platform_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("login_identifier", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("auth_method", sa.String(length=40), nullable=False, server_default="manual_only"),
        sa.Column("vault_ref", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("owner_hint", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("scope", sa.String(length=40), nullable=False, server_default="shared"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("regions_allowed", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["platform_id"], ["source_platforms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_accounts_tenant_id", "platform_accounts", ["tenant_id"])
    op.create_index("ix_platform_accounts_platform_id", "platform_accounts", ["platform_id"])
    op.create_index("ix_platform_accounts_status", "platform_accounts", ["status"])

    op.create_table(
        "platform_connectors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("platform_id", sa.String(length=36), nullable=False),
        sa.Column("provider_key", sa.String(length=80), nullable=False),
        sa.Column("auth_mode", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("capabilities", sa.Text(), nullable=False, server_default="draft_only"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="manual_only"),
        sa.Column("env_var", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["platform_id"], ["source_platforms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_connectors_tenant_id", "platform_connectors", ["tenant_id"])
    op.create_index("ix_platform_connectors_platform_id", "platform_connectors", ["platform_id"])
    op.create_index("ix_platform_connectors_status", "platform_connectors", ["status"])

    op.add_column("distribution_jobs", sa.Column("platform_id", sa.String(length=36), nullable=True))
    op.add_column("distribution_jobs", sa.Column("account_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_distribution_jobs_platform_id", "distribution_jobs", "source_platforms", ["platform_id"], ["id"])
    op.create_foreign_key("fk_distribution_jobs_account_id", "distribution_jobs", "platform_accounts", ["account_id"], ["id"])
    op.create_index("ix_distribution_jobs_platform_id", "distribution_jobs", ["platform_id"])
    op.create_index("ix_distribution_jobs_account_id", "distribution_jobs", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_distribution_jobs_account_id", table_name="distribution_jobs")
    op.drop_index("ix_distribution_jobs_platform_id", table_name="distribution_jobs")
    op.drop_constraint("fk_distribution_jobs_account_id", "distribution_jobs", type_="foreignkey")
    op.drop_constraint("fk_distribution_jobs_platform_id", "distribution_jobs", type_="foreignkey")
    op.drop_column("distribution_jobs", "account_id")
    op.drop_column("distribution_jobs", "platform_id")
    op.drop_index("ix_platform_connectors_status", table_name="platform_connectors")
    op.drop_index("ix_platform_connectors_platform_id", table_name="platform_connectors")
    op.drop_index("ix_platform_connectors_tenant_id", table_name="platform_connectors")
    op.drop_table("platform_connectors")
    op.drop_index("ix_platform_accounts_status", table_name="platform_accounts")
    op.drop_index("ix_platform_accounts_platform_id", table_name="platform_accounts")
    op.drop_index("ix_platform_accounts_tenant_id", table_name="platform_accounts")
    op.drop_table("platform_accounts")
    op.drop_index("ix_source_platforms_status", table_name="source_platforms")
    op.drop_index("ix_source_platforms_platform_key", table_name="source_platforms")
    op.drop_index("ix_source_platforms_tenant_id", table_name="source_platforms")
    op.drop_table("source_platforms")

    op.drop_column("onsite_issues", "result_url")
    op.drop_column("onsite_issues", "acceptance_criteria")
    for table in ("geo_tickets", "onsite_issues"):
        op.drop_column(table, "closed_at")
        op.drop_column(table, "last_checked_at")
        op.drop_column(table, "blocked_reason")
        op.drop_column(table, "retest_result")
        op.drop_column(table, "retest_method")
        op.drop_column(table, "recommended_action")
        op.drop_column(table, "owner_hint")
        op.drop_column(table, "priority")
