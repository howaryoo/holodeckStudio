"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "production_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("max_feedback_iterations", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("conflict_escalation_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("quality_gate_threshold", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("human_approval_timeout_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("model_overrides", postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        "productions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("theme_prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("mode", sa.String(), nullable=False, server_default="autonomous"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("production_configs.id"), nullable=True),
    )

    op.create_table(
        "franchise_bibles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "bible_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bible_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("franchise_bibles.id"), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_bible_entries_category", "bible_entries", ["category"])
    op.create_index("ix_bible_entries_bible_id", "bible_entries", ["bible_id"])

    op.create_table(
        "episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("production_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("productions.id"), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="concept"),
        sa.Column("current_stage", sa.String(), nullable=False, server_default="concept"),
        sa.Column("feedback_iterations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("stage_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("input_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_data", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="3"),
    )

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stages.id"), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("episodes.id"), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stages.id"), nullable=False),
        sa.Column("reviewer_type", sa.String(), nullable=False),
        sa.Column("narrative_score", sa.Integer(), nullable=True),
        sa.Column("consistency_score", sa.Integer(), nullable=True),
        sa.Column("pacing_score", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "approval_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stages.id"), nullable=False),
        sa.Column("checkpoint_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("reviewer", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("timeout_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("production_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("productions.id"), nullable=False),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("episodes.id"), nullable=True),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stages.id"), nullable=True),
        sa.Column("agent_role", sa.String(), nullable=False),
        sa.Column("langfuse_trace_id", sa.Text(), nullable=True),
        sa.Column("model_provider", sa.Text(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_executions")
    op.drop_table("approval_checkpoints")
    op.drop_table("reviews")
    op.drop_table("assets")
    op.drop_table("stages")
    op.drop_table("episodes")
    op.drop_table("bible_entries")
    op.drop_table("franchise_bibles")
    op.drop_table("productions")
    op.drop_table("production_configs")
    op.execute("DROP EXTENSION IF EXISTS vector")