"""geo tickets, china engines prep, link verify fields

Revision ID: 004_three_chains
Revises: 003_onsite_offsite_dist
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_three_chains"
down_revision: Union[str, None] = "003_onsite_offsite_dist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("geo_prompts", sa.Column("diagnosis", sa.String(40), nullable=False, server_default="untested"))
    op.create_table(
        "geo_tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("prompt_id", sa.String(36), sa.ForeignKey("geo_prompts.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("diagnosis", sa.String(40), nullable=False, server_default="untested"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("acceptance_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("verified_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_geo_tickets_tenant_id", "geo_tickets", ["tenant_id"])
    op.create_index("ix_geo_tickets_prompt_id", "geo_tickets", ["prompt_id"])
    op.create_index("ix_geo_tickets_status", "geo_tickets", ["status"])

    op.add_column("backlink_gaps", sa.Column("link_url", sa.String(500)))
    op.add_column("backlink_gaps", sa.Column("kind", sa.String(20), nullable=False, server_default="competitor"))
    op.add_column(
        "backlink_gaps",
        sa.Column("verify_status", sa.String(20), nullable=False, server_default="unverified"),
    )


def downgrade() -> None:
    op.drop_column("backlink_gaps", "verify_status")
    op.drop_column("backlink_gaps", "kind")
    op.drop_column("backlink_gaps", "link_url")
    op.drop_table("geo_tickets")
    op.drop_column("geo_prompts", "diagnosis")
