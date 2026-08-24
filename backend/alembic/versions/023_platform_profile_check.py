"""store public profile URL and last check

Revision ID: 023_platform_profile_check
Revises: 022_usage_quotas
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa


revision = "023_platform_profile_check"
down_revision = "022_usage_quotas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("source_platforms", sa.Column("profile_url", sa.String(length=500), nullable=False, server_default=""))
    op.add_column("source_platforms", sa.Column("profile_http_status", sa.Integer(), nullable=True))
    op.add_column("source_platforms", sa.Column("profile_is_live", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("source_platforms", sa.Column("profile_site_found", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("source_platforms", sa.Column("profile_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_platforms", sa.Column("profile_note", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("source_platforms", "profile_note")
    op.drop_column("source_platforms", "profile_checked_at")
    op.drop_column("source_platforms", "profile_site_found")
    op.drop_column("source_platforms", "profile_is_live")
    op.drop_column("source_platforms", "profile_http_status")
    op.drop_column("source_platforms", "profile_url")
