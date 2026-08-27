"""record where a buyer question came from

Revision ID: 024_geo_prompt_source
Revises: 023_platform_profile_check
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "024_geo_prompt_source"
down_revision = "023_platform_profile_check"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("geo_prompts", sa.Column("recorded_from", sa.String(length=40), nullable=False, server_default=""))
    op.add_column("geo_prompts", sa.Column("source_note", sa.String(length=200), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("geo_prompts", "source_note")
    op.drop_column("geo_prompts", "recorded_from")
