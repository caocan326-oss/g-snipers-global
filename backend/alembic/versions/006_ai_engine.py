"""AI engine runs and evidence fields

Revision ID: 006_ai_engine
Revises: 005_onsite_severity
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_ai_engine"
down_revision: Union[str, None] = "005_onsite_severity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("geo_prompts", sa.Column("ai_status", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("geo_prompts", sa.Column("evidence", sa.Text(), nullable=False, server_default=""))
    op.add_column("geo_assets", sa.Column("ai_status", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("geo_tickets", sa.Column("ai_status", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("geo_tickets", sa.Column("ai_review", sa.Text(), nullable=False, server_default=""))
    op.add_column("geo_tickets", sa.Column("evidence", sa.Text(), nullable=False, server_default=""))
    op.add_column("onsite_issues", sa.Column("ai_status", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("onsite_issues", sa.Column("ai_diagnosis", sa.Text(), nullable=False, server_default=""))
    op.add_column("onsite_issues", sa.Column("ai_review", sa.Text(), nullable=False, server_default=""))
    op.add_column("onsite_issues", sa.Column("ai_review_verdict", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("onsite_issues", sa.Column("evidence", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("ai_status", sa.String(20), nullable=False, server_default="untested"))
    op.add_column("backlink_gaps", sa.Column("ai_review", sa.Text(), nullable=False, server_default=""))
    op.add_column("backlink_gaps", sa.Column("evidence", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("chain", sa.String(20), nullable=False),
        sa.Column("step", sa.String(20), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("output", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_runs_tenant_id", "ai_runs", ["tenant_id"])
    op.create_index("ix_ai_runs_target_id", "ai_runs", ["target_id"])


def downgrade() -> None:
    op.drop_table("ai_runs")
    op.drop_column("backlink_gaps", "evidence")
    op.drop_column("backlink_gaps", "ai_review")
    op.drop_column("backlink_gaps", "ai_status")
    op.drop_column("onsite_issues", "evidence")
    op.drop_column("onsite_issues", "ai_review_verdict")
    op.drop_column("onsite_issues", "ai_review")
    op.drop_column("onsite_issues", "ai_diagnosis")
    op.drop_column("onsite_issues", "ai_status")
    op.drop_column("geo_tickets", "evidence")
    op.drop_column("geo_tickets", "ai_review")
    op.drop_column("geo_tickets", "ai_status")
    op.drop_column("geo_assets", "ai_status")
    op.drop_column("geo_prompts", "evidence")
    op.drop_column("geo_prompts", "ai_status")
