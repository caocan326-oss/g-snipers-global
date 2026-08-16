"""offsite issue execution fields

Revision ID: 018_offsite_issue_execution
Revises: 017_integration_settings
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "018_offsite_issue_execution"
down_revision = "017_integration_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backlink_gaps", sa.Column("title", sa.String(length=300), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("issue_type", sa.String(length=40), nullable=False, server_default="competitor_gap"))
    op.add_column("backlink_gaps", sa.Column("source", sa.String(length=40), nullable=False, server_default="manual"))
    op.add_column("backlink_gaps", sa.Column("source_platform_id", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("priority", sa.String(length=10), nullable=False, server_default="P2"))
    op.add_column("backlink_gaps", sa.Column("owner_hint", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("acceptance_criteria", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("recommended_action", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("retest_method", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("retest_result", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("result_url", sa.String(length=500), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("blocked_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("backlink_gaps", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("distribution_jobs", sa.Column("gap_id", sa.String(length=36), nullable=True))
    op.add_column("distribution_jobs", sa.Column("task_type", sa.String(length=40), nullable=False, server_default="profile_create"))
    op.add_column("distribution_jobs", sa.Column("owner_hint", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("distribution_jobs", sa.Column("result_url", sa.String(length=500), nullable=False, server_default=""))
    op.add_column("distribution_jobs", sa.Column("verify_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("distribution_jobs", sa.Column("blocked_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("distribution_jobs", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("distribution_jobs", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_distribution_jobs_gap_id", "distribution_jobs", "backlink_gaps", ["gap_id"], ["id"])
    op.create_index("ix_distribution_jobs_gap_id", "distribution_jobs", ["gap_id"])


def downgrade() -> None:
    op.drop_index("ix_distribution_jobs_gap_id", table_name="distribution_jobs")
    op.drop_constraint("fk_distribution_jobs_gap_id", "distribution_jobs", type_="foreignkey")
    op.drop_column("distribution_jobs", "last_checked_at")
    op.drop_column("distribution_jobs", "due_at")
    op.drop_column("distribution_jobs", "blocked_reason")
    op.drop_column("distribution_jobs", "verify_status")
    op.drop_column("distribution_jobs", "result_url")
    op.drop_column("distribution_jobs", "owner_hint")
    op.drop_column("distribution_jobs", "task_type")
    op.drop_column("distribution_jobs", "gap_id")

    op.drop_column("backlink_gaps", "closed_at")
    op.drop_column("backlink_gaps", "last_checked_at")
    op.drop_column("backlink_gaps", "blocked_reason")
    op.drop_column("backlink_gaps", "result_url")
    op.drop_column("backlink_gaps", "retest_result")
    op.drop_column("backlink_gaps", "retest_method")
    op.drop_column("backlink_gaps", "recommended_action")
    op.drop_column("backlink_gaps", "acceptance_criteria")
    op.drop_column("backlink_gaps", "owner_hint")
    op.drop_column("backlink_gaps", "priority")
    op.drop_column("backlink_gaps", "source_platform_id")
    op.drop_column("backlink_gaps", "source")
    op.drop_column("backlink_gaps", "issue_type")
    op.drop_column("backlink_gaps", "title")
