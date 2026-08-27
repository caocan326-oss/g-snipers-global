"""cite-pack loop on recorded buyer questions

Revision ID: 025_geo_cite_loop
Revises: 024_geo_prompt_source
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "025_geo_cite_loop"
down_revision = "024_geo_prompt_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("geo_prompts", sa.Column("cite_stage", sa.String(length=20), nullable=False, server_default="draft"))
    op.add_column("geo_prompts", sa.Column("cite_published_url", sa.String(length=500), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("geo_prompts", "cite_published_url")
    op.drop_column("geo_prompts", "cite_stage")
