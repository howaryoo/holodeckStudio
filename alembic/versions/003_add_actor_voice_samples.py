"""add actor_voice_samples table

Revision ID: 003
Revises: 002
Create Date: 2026-06-25
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actor_voice_samples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bible_id",
            UUID(as_uuid=True),
            sa.ForeignKey("franchise_bibles.id"),
            nullable=False,
        ),
        sa.Column("character_name", sa.String(), nullable=False),
        sa.Column("sample_file_path", sa.String(), nullable=False),
        sa.Column("source_format", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("elevenlabs_voice_id", sa.String(), nullable=True),
        sa.Column(
            "upload_date",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.CheckConstraint(
            "duration_seconds >= 10.0 AND duration_seconds <= 600.0",
            name="ck_voice_sample_duration_range",
        ),
        sa.CheckConstraint(
            "source_format IN ('mp3', 'wav', 'ogg', 'flac')",
            name="ck_voice_sample_source_format",
        ),
    )
    op.create_index(
        "ix_voice_samples_bible_char",
        "actor_voice_samples",
        ["bible_id", "character_name"],
    )
    op.create_index(
        "ix_voice_samples_active",
        "actor_voice_samples",
        ["is_active"],
    )
    op.create_index(
        "uix_voice_samples_active_char",
        "actor_voice_samples",
        ["bible_id", "character_name"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uix_voice_samples_active_char", table_name="actor_voice_samples")
    op.drop_index("ix_voice_samples_active", table_name="actor_voice_samples")
    op.drop_index("ix_voice_samples_bible_char", table_name="actor_voice_samples")
    op.drop_table("actor_voice_samples")
