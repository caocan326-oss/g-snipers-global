"""gsc connections

Revision ID: 012_gsc_connections
Revises: 011_geo_observation_evidence
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "012_gsc_connections"
down_revision = "011_geo_observation_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gsc_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("site_url", sa.String(length=700), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=False),
        sa.Column("connected_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connected_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_gsc_connections_tenant"),
    )
    op.create_index(op.f("ix_gsc_connections_status"), "gsc_connections", ["status"], unique=False)
    op.create_index(op.f("ix_gsc_connections_tenant_id"), "gsc_connections", ["tenant_id"], unique=False)

    op.create_table(
        "gsc_sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("date_start", sa.String(length=20), nullable=False),
        sa.Column("date_end", sa.String(length=20), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["connection_id"], ["gsc_connections.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gsc_sync_runs_connection_id"), "gsc_sync_runs", ["connection_id"], unique=False)
    op.create_index(op.f("ix_gsc_sync_runs_status"), "gsc_sync_runs", ["status"], unique=False)
    op.create_index(op.f("ix_gsc_sync_runs_tenant_id"), "gsc_sync_runs", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gsc_sync_runs_tenant_id"), table_name="gsc_sync_runs")
    op.drop_index(op.f("ix_gsc_sync_runs_status"), table_name="gsc_sync_runs")
    op.drop_index(op.f("ix_gsc_sync_runs_connection_id"), table_name="gsc_sync_runs")
    op.drop_table("gsc_sync_runs")
    op.drop_index(op.f("ix_gsc_connections_tenant_id"), table_name="gsc_connections")
    op.drop_index(op.f("ix_gsc_connections_status"), table_name="gsc_connections")
    op.drop_table("gsc_connections")
