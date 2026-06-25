# Data Model: 11Labs Voice Clone Integration

**Date**: 2026-06-25
**Purpose**: Define entities, relationships, and database schema for voice cloning feature

> **Revised 2026-06-25**: Fixed UUID primary keys (was Integer), character reference strategy
> (was FK to non-existent `characters` table — now `bible_id` FK + `character_name` string),
> Pydantic v2 style (`model_config = ConfigDict`), duration bounds (15–600s), and removed
> `VoiceSynthesisConfig` DB table (replaced by `Settings` env vars).

---

## Entity Definitions

### 1. ActorVoiceSample (ORM + PostgreSQL)

Represents a stored audio sample for an actor, used to generate a cloned voice ID via the
11Labs API. One active sample per character per franchise bible.

**Core Fields**:
- `id` (UUID, Primary Key): Unique identifier — consistent with all existing ORM tables
- `bible_id` (UUID, Foreign Key → `franchise_bibles.id`): Which franchise this sample belongs to
- `character_name` (String): Display name (e.g., `"Rachel Green"`) — business key for lookup
- `sample_file_path` (String): Path to audio file in MinIO
  (`"voice-samples/{bible_id}/{char_slug}/sample.mp3"`)
- `source_format` (String): Original format (`"mp3"`, `"wav"`, `"ogg"`, `"flac"`)
- `duration_seconds` (Float): Computed duration via `ffprobe` (validated 15–600 seconds)
- `is_active` (Boolean, default=`True`): Enable/disable sample without deletion (soft-delete)

**11Labs Integration Fields**:
- `elevenlabs_voice_id` (String, Nullable): Cloned voice ID from `client.voices.add()`.
  - `NULL` until first production use.
  - Persisted after first clone to avoid re-calling the API on subsequent productions.
  - Deterministic: same sample file always generates the same voice ID (11Labs guarantee).

**Metadata Fields**:
- `upload_date` (DateTime, server_default=`now()`): When sample was added
- `created_by` (String, Nullable): Admin who uploaded the sample
- `description` (String, Nullable): Quality notes or version info

**Validation Rules**:
- `duration_seconds` ∈ [15.0, 600.0] — enforced by Pydantic schema and DB check constraint
- `source_format` ∈ `{"mp3", "wav", "ogg", "flac"}` — validated before MinIO upload
- `sample_file_path` must be non-empty
- `bible_id` must reference an existing `franchise_bibles` record (FK enforced by DB)
- Only one `ActorVoiceSample` with `is_active=True` per `(bible_id, character_name)` pair
  — enforced by a partial unique index

**Lifecycle**:
```
Upload → ffprobe validate (format, duration) → MinIO upload
       → Create DB record (elevenlabs_voice_id=NULL, is_active=True)
       → First Production Use → client.voices.add() → cache voice_id → UPDATE DB
       → Subsequent Productions → use cached voice_id (no clone API call)
       → Replace → new sample added, old set is_active=False
       → Disable → SET is_active=False (data + MinIO file preserved)
```

---

### 2. VoiceSynthesisProvider (Protocol — application layer only)

Not a database entity. Defines the contract for any voice synthesis backend.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class VoiceSynthesisProvider(Protocol):
    async def synthesize(
        self,
        text: str,
        char_name: str,
        output_path: str,
        context: dict,
    ) -> bool:
        """Generate audio for `text` and write MP3 to `output_path`. Returns success."""
        ...
```

Concrete implementations:
- `ElevenLabsProvider`: calls `client.text_to_speech.convert()`, falls back on error
- `PiperProvider`: wraps existing `_synthesize_with_piper()` + `_wav_to_mp3()` helpers

---

### 3. VoiceSynthesisSettings (Pydantic Settings extension — not a DB table)

New fields added to `src/holodeck/config/settings.py`:

```python
# ElevenLabs integration
elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key")
elevenlabs_voice_model: str = Field(
    default="eleven_monolingual_v1",
    description="ElevenLabs TTS model identifier",
)
elevenlabs_voice_stability: float = Field(
    default=0.5, ge=0.0, le=1.0,
    description="Voice stability [0.0–1.0]; higher = more consistent",
)
elevenlabs_similarity_boost: float = Field(
    default=0.75, ge=0.0, le=1.0,
    description="Similarity to original [0.0–1.0]; higher = closer clone",
)
elevenlabs_use_speaker_boost: bool = Field(
    default=False,
    description="Enable 11Labs speaker boost for audio quality enhancement",
)
```

---

## Database Schema

### Migration 003: Add actor_voice_samples

```python
# alembic/versions/003_add_actor_voice_samples.py

"""add actor_voice_samples table

Revision ID: 003
Revises: 002
Create Date: 2026-06-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actor_voice_samples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("bible_id", UUID(as_uuid=True), sa.ForeignKey("franchise_bibles.id"), nullable=False),
        sa.Column("character_name", sa.String(), nullable=False),
        sa.Column("sample_file_path", sa.String(), nullable=False),
        sa.Column("source_format", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("elevenlabs_voice_id", sa.String(), nullable=True),
        sa.Column("upload_date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.CheckConstraint("duration_seconds >= 15.0 AND duration_seconds <= 600.0", name="ck_duration_range"),
        sa.CheckConstraint("source_format IN ('mp3', 'wav', 'ogg', 'flac')", name="ck_source_format"),
    )
    # Fast lookups: samples by character for a given bible
    op.create_index("ix_voice_samples_bible_char", "actor_voice_samples", ["bible_id", "character_name"])
    # Active-only filter (most common query)
    op.create_index("ix_voice_samples_active", "actor_voice_samples", ["is_active"])
    # Enforce one active sample per character per bible
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
```

---

## Pydantic Schemas (Application Layer, Pydantic v2)

```python
# src/holodeck/agents/audio/schemas.py

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ActorVoiceSampleCreate(BaseModel):
    bible_id: UUID
    character_name: str
    sample_file_path: str
    source_format: str = Field(pattern=r"^(mp3|wav|ogg|flac)$")
    duration_seconds: float = Field(ge=15.0, le=600.0)
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
```

---

## ORM Model

```python
# Addition to src/holodeck/storage/postgres.py

from uuid import uuid4

class ActorVoiceSample(Base):
    __tablename__ = "actor_voice_samples"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bible_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("franchise_bibles.id"), nullable=False
    )
    character_name: Mapped[str] = mapped_column(String, nullable=False)
    sample_file_path: Mapped[str] = mapped_column(String, nullable=False)
    source_format: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(nullable=False)
    elevenlabs_voice_id: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    bible: Mapped["FranchiseBible"] = relationship("FranchiseBible")
```

---

## Entity Relationships

```
FranchiseBible (existing)
    ↓ 1:N
ActorVoiceSample
    - Each bible has 0 or more voice samples (one per character at most active at once)
    - Each sample belongs to exactly 1 bible + is keyed by character_name string

ActorVoiceSample → 11Labs API → elevenlabs_voice_id (external, deterministic)
    - Cloned once per sample on first production use
    - Cached in DB for all subsequent productions
```

---

## State Transitions

```
[Created] → upload_date set, is_active=True, elevenlabs_voice_id=NULL
    ↓
[First Production Use] → client.voices.add(files=[sample_file_path]) → voice_id returned
    ↓
[Voice ID Cached] → UPDATE actor_voice_samples SET elevenlabs_voice_id=... → is_active=True
    ↓
[Reused] → subsequent productions read voice_id from DB, no clone API call
    
Parallel path (replacement):
    ↓
[New Sample Uploaded] → old sample SET is_active=False, new sample created with voice_id=NULL
    
Parallel path (disable):
    ↓
[Disabled] → SET is_active=False, data + MinIO file preserved for audit
```

---

## Key Constraints & Business Rules

1. **One Active Sample Per Character**: Enforced by partial unique index on
   `(bible_id, character_name)` where `is_active=TRUE`. Application layer sets old sample
   `is_active=False` before inserting new one within a transaction.

2. **Voice ID Determinism**: 11Labs guarantees same sample → same voice_id. Enables safe caching.

3. **Duration Range**: 15–600 seconds. Enforced at Pydantic schema level (validation on upload)
   and at DB level (`CHECK` constraint in migration).

4. **Format Allowlist**: `{mp3, wav, ogg, flac}`. Enforced at Pydantic schema and DB `CHECK`.

5. **Bible Existence**: `bible_id` FK ensures the franchise bible exists before a voice sample
   can be associated with it.

6. **Fallback to Piper**: Characters with no active `ActorVoiceSample` (or with
   `elevenlabs_api_key=""`) transparently use `PiperProvider`. No error raised.

---

## Indexes for Performance

| Table | Index | Purpose |
|-------|-------|---------|
| `actor_voice_samples` | `ix_voice_samples_bible_char (bible_id, character_name)` | Fast character lookup by franchise |
| `actor_voice_samples` | `ix_voice_samples_active (is_active)` | Filter active samples only |
| `actor_voice_samples` | `uix_voice_samples_active_char` (partial unique) | Enforce 1-active-sample-per-character |

---

## Data Retention

- **`actor_voice_samples`** rows: retained indefinitely; `is_active=False` is soft-delete.
- **MinIO files**: retained until manually removed or franchise deleted. `sample_file_path`
  is the authoritative pointer; file and DB record must stay in sync (delete both or neither).
