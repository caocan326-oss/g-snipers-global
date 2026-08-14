"""geo monitoring and assets

Revision ID: 002_geo
Revises: 001_initial
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_geo"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "geo_prompts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id")),
        sa.Column("seo_page_id", sa.String(36), sa.ForeignKey("seo_pages.id")),
        sa.Column("demand_signal_id", sa.String(36), sa.ForeignKey("demand_signals.id")),
        sa.Column("prompt_text", sa.String(500), nullable=False),
        sa.Column("locale", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_geo_prompts_tenant_id", "geo_prompts", ["tenant_id"])
    op.create_index("ix_geo_prompts_market_id", "geo_prompts", ["market_id"])

    op.create_table(
        "geo_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("prompt_id", sa.String(36), sa.ForeignKey("geo_prompts.id"), nullable=False),
        sa.Column("engine", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("notes", sa.Text()),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("observed_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("prompt_id", "engine", name="uq_geo_obs_prompt_engine"),
    )
    op.create_index("ix_geo_observations_tenant_id", "geo_observations", ["tenant_id"])
    op.create_index("ix_geo_observations_prompt_id", "geo_observations", ["prompt_id"])

    op.create_table(
        "geo_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "kind", name="uq_geo_assets_tenant_kind"),
    )
    op.create_index("ix_geo_assets_tenant_id", "geo_assets", ["tenant_id"])

    op.create_table(
        "geo_checklist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("seo_page_id", sa.String(36), sa.ForeignKey("seo_pages.id"), nullable=False),
        sa.Column("item_key", sa.String(40), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("seo_page_id", "item_key", name="uq_geo_check_page_key"),
    )
    op.create_index("ix_geo_checklist_items_tenant_id", "geo_checklist_items", ["tenant_id"])
    op.create_index("ix_geo_checklist_items_seo_page_id", "geo_checklist_items", ["seo_page_id"])


def downgrade() -> None:
    op.drop_table("geo_checklist_items")
    op.drop_table("geo_assets")
    op.drop_table("geo_observations")
    op.drop_table("geo_prompts")
