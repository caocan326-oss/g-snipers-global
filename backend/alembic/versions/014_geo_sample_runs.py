"""geo sample runs

Revision ID: 014_geo_sample_runs
Revises: 013_data_sync_and_indexnow
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "014_geo_sample_runs"
down_revision = "013_data_sync_and_indexnow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "geo_sample_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("protocol_version", sa.String(length=80), nullable=False, server_default="geo-test-protocol-v1"),
        sa.Column("prompt_set_id", sa.String(length=120), nullable=False, server_default="manual-panel"),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("brand_names", sa.Text(), nullable=False, server_default=""),
        sa.Column("engines", sa.Text(), nullable=False, server_default=""),
        sa.Column("trials_per_prompt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("region_hint", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("operator_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="done"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_geo_sample_runs_config_hash"), "geo_sample_runs", ["config_hash"], unique=False)
    op.create_index(op.f("ix_geo_sample_runs_status"), "geo_sample_runs", ["status"], unique=False)
    op.create_index(op.f("ix_geo_sample_runs_tenant_id"), "geo_sample_runs", ["tenant_id"], unique=False)

    op.create_table(
        "geo_sample_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("prompt_id", sa.String(length=36), nullable=False),
        sa.Column("observation_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_id", sa.String(length=80), nullable=False),
        sa.Column("trial_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("engine", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False, server_default="manual"),
        sa.Column("web_grounded", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("surface", sa.String(length=60), nullable=False, server_default="manual_ai_answer"),
        sa.Column("prompt_text_hash", sa.String(length=64), nullable=False),
        sa.Column("answer_text_hash", sa.String(length=64), nullable=False),
        sa.Column("answer_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("mentioned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("citations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("owned_citations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("third_party_citations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("brand_hits", sa.Text(), nullable=False, server_default=""),
        sa.Column("competitor_hits", sa.Text(), nullable=False, server_default=""),
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("verification_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("sampled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["observation_id"], ["geo_observations.id"]),
        sa.ForeignKeyConstraint(["prompt_id"], ["geo_prompts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["geo_sample_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "prompt_id", "engine", "trial_index", name="uq_geo_sample_trial"),
    )
    op.create_index(op.f("ix_geo_sample_results_evidence_id"), "geo_sample_results", ["evidence_id"], unique=True)
    op.create_index(op.f("ix_geo_sample_results_observation_id"), "geo_sample_results", ["observation_id"], unique=False)
    op.create_index(op.f("ix_geo_sample_results_prompt_id"), "geo_sample_results", ["prompt_id"], unique=False)
    op.create_index(op.f("ix_geo_sample_results_run_id"), "geo_sample_results", ["run_id"], unique=False)
    op.create_index(op.f("ix_geo_sample_results_tenant_id"), "geo_sample_results", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_geo_sample_results_tenant_id"), table_name="geo_sample_results")
    op.drop_index(op.f("ix_geo_sample_results_run_id"), table_name="geo_sample_results")
    op.drop_index(op.f("ix_geo_sample_results_prompt_id"), table_name="geo_sample_results")
    op.drop_index(op.f("ix_geo_sample_results_observation_id"), table_name="geo_sample_results")
    op.drop_index(op.f("ix_geo_sample_results_evidence_id"), table_name="geo_sample_results")
    op.drop_table("geo_sample_results")
    op.drop_index(op.f("ix_geo_sample_runs_tenant_id"), table_name="geo_sample_runs")
    op.drop_index(op.f("ix_geo_sample_runs_status"), table_name="geo_sample_runs")
    op.drop_index(op.f("ix_geo_sample_runs_config_hash"), table_name="geo_sample_runs")
    op.drop_table("geo_sample_runs")
