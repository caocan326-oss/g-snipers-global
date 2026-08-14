"""onsite severity, canonical, analyzed_at

Revision ID: 005_onsite_severity
Revises: 004_three_chains
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_onsite_severity"
down_revision: Union[str, None] = "004_three_chains"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("site_pages", sa.Column("canonical", sa.String(500), nullable=False, server_default=""))
    op.add_column("site_pages", sa.Column("analyzed_at", sa.DateTime(timezone=True)))
    op.add_column("onsite_issues", sa.Column("severity", sa.String(10), nullable=False, server_default="low"))


def downgrade() -> None:
    op.drop_column("onsite_issues", "severity")
    op.drop_column("site_pages", "analyzed_at")
    op.drop_column("site_pages", "canonical")
