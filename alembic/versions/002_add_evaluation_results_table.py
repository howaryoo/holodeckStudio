"""add evaluation_results table

Revision ID: 002
Revises: 001
Create Date: 2026-06-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_results",
        sa.Column("result_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("script_id", sa.String(), nullable=False),
        sa.Column("golden_entry_id", sa.String(), nullable=False, index=True),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("passed_quality_gate", sa.Boolean(), nullable=False),
        sa.Column("red_flags_triggered", JSONB(), nullable=False, server_default="[]"),
        sa.Column("dimension_scores", JSONB(), nullable=False),
        sa.Column("guideline_comparison", JSONB(), nullable=False, server_default="{}"),
        sa.Column("previous_score", sa.Float(), nullable=True),
        sa.Column("regression_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "evaluation_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_evaluation_results_golden_entry_timestamp",
        "evaluation_results",
        ["golden_entry_id", "evaluation_timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_golden_entry_timestamp", table_name="evaluation_results")
    op.drop_table("evaluation_results")
