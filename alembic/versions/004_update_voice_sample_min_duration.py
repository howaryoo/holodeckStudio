"""update voice sample min duration to 10s

Revision ID: 004
Revises: 003
Create Date: 2026-06-25
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_voice_sample_duration_range", "actor_voice_samples")
    op.create_check_constraint(
        "ck_voice_sample_duration_range",
        "actor_voice_samples",
        "duration_seconds >= 10.0 AND duration_seconds <= 600.0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_voice_sample_duration_range", "actor_voice_samples")
    op.create_check_constraint(
        "ck_voice_sample_duration_range",
        "actor_voice_samples",
        "duration_seconds >= 15.0 AND duration_seconds <= 600.0",
    )
