"""geo observation evidence

Revision ID: 011_geo_observation_evidence
Revises: 010_page_fetch_evidence_fields
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "011_geo_observation_evidence"
down_revision = "010_page_fetch_evidence_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("geo_observations", sa.Column("surface", sa.String(length=60), nullable=False, server_default="manual_ai_answer"))
    op.add_column("geo_observations", sa.Column("sample_type", sa.String(length=40), nullable=False, server_default="manual"))
    op.add_column("geo_observations", sa.Column("response_excerpt", sa.Text(), nullable=False, server_default=""))
    op.add_column("geo_observations", sa.Column("citation_urls", sa.Text(), nullable=False, server_default=""))
    op.add_column("geo_observations", sa.Column("brand_mentions", sa.Text(), nullable=False, server_default=""))
    op.add_column("geo_observations", sa.Column("competitor_mentions", sa.Text(), nullable=False, server_default=""))
    op.add_column("geo_observations", sa.Column("interpretation_note", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("geo_observations", "interpretation_note")
    op.drop_column("geo_observations", "competitor_mentions")
    op.drop_column("geo_observations", "brand_mentions")
    op.drop_column("geo_observations", "citation_urls")
    op.drop_column("geo_observations", "response_excerpt")
    op.drop_column("geo_observations", "sample_type")
    op.drop_column("geo_observations", "surface")
