from __future__ import annotations

from datetime import datetime  # noqa: TC003
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field


class ActorVoiceSampleCreate(BaseModel):
    bible_id: UUID
    character_name: str
    sample_file_path: str
    source_format: str = Field(pattern=r"^(mp3|wav|ogg|flac)$")
    duration_seconds: float = Field(ge=10.0, le=600.0)
    created_by: str | None = None
    description: str | None = None


class ActorVoiceSample(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bible_id: UUID
    character_name: str
    sample_file_path: str
    source_format: str
    duration_seconds: float
    elevenlabs_voice_id: str | None = None
    upload_date: datetime
    created_by: str | None = None
    description: str | None = None
    is_active: bool = True
