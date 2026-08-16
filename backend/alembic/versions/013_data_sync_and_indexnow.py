"""data sync and indexnow

Revision ID: 013_data_sync_and_indexnow
Revises: 012_gsc_connections
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "013_data_sync_and_indexnow"
down_revision = "012_gsc_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("submitted", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_sync_runs_source"), "data_sync_runs", ["source"], unique=False)
    op.create_index(op.f("ix_data_sync_runs_status"), "data_sync_runs", ["status"], unique=False)
    op.create_index(op.f("ix_data_sync_runs_tenant_id"), "data_sync_runs", ["tenant_id"], unique=False)

    op.create_table(
        "indexnow_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("key_location", sa.String(length=700), nullable=False),
        sa.Column("urls", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("submitted_by", sa.String(length=36), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_indexnow_submissions_status"), "indexnow_submissions", ["status"], unique=False)
    op.create_index(op.f("ix_indexnow_submissions_tenant_id"), "indexnow_submissions", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_indexnow_submissions_tenant_id"), table_name="indexnow_submissions")
    op.drop_index(op.f("ix_indexnow_submissions_status"), table_name="indexnow_submissions")
    op.drop_table("indexnow_submissions")
    op.drop_index(op.f("ix_data_sync_runs_tenant_id"), table_name="data_sync_runs")
    op.drop_index(op.f("ix_data_sync_runs_status"), table_name="data_sync_runs")
    op.drop_index(op.f("ix_data_sync_runs_source"), table_name="data_sync_runs")
    op.drop_table("data_sync_runs")
