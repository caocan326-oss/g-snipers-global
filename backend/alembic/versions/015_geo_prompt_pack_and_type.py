"""geo prompt pack and type

Revision ID: 015_geo_prompt_pack_and_type
Revises: 014_geo_sample_runs
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "015_geo_prompt_pack_and_type"
down_revision = "014_geo_sample_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("geo_prompts", sa.Column("prompt_pack_id", sa.String(length=120), nullable=False, server_default="custom"))
    op.add_column("geo_prompts", sa.Column("prompt_key", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("geo_prompts", sa.Column("prompt_type", sa.String(length=40), nullable=False, server_default="custom"))
    op.add_column("geo_sample_results", sa.Column("prompt_type", sa.String(length=40), nullable=False, server_default="custom"))


def downgrade() -> None:
    op.drop_column("geo_sample_results", "prompt_type")
    op.drop_column("geo_prompts", "prompt_type")
    op.drop_column("geo_prompts", "prompt_key")
    op.drop_column("geo_prompts", "prompt_pack_id")
