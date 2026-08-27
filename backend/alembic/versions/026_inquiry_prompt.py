"""link an inquiry to a recorded buyer question

Revision ID: 026_inquiry_prompt
Revises: 025_geo_cite_loop
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = "026_inquiry_prompt"
down_revision = "025_geo_cite_loop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inquiries", sa.Column("related_prompt_id", sa.String(length=36), nullable=True))
    op.create_index("ix_inquiries_related_prompt_id", "inquiries", ["related_prompt_id"])


def downgrade() -> None:
    op.drop_index("ix_inquiries_related_prompt_id", table_name="inquiries")
    op.drop_column("inquiries", "related_prompt_id")
