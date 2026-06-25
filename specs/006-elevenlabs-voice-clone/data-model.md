# Data Model: 11Labs Voice Clone Integration

**Date**: 2026-06-25  
**Purpose**: Define entities, relationships, and database schema for voice cloning feature

## Entity Definitions

### 1. ActorVoiceSample

Represents a stored audio sample for an actor, used to generate voice IDs via 11Labs API.

**Core Fields**:
- `id` (Integer, Primary Key): Unique identifier
- `character_id` (Integer, Foreign Key → characters.id): Reference to character being voiced
- `character_name` (String): Display name (e.g., "Rachel Green") — denormalized for clarity
- `sample_file_path` (String): Path to audio file in MinIO (e.g., "voice-samples/rachel_green/sample.mp3")
- `source_format` (String): Original format (MP3, WAV, OGG, FLAC)
- `duration_seconds` (Float): Computed duration of sample (30–600 seconds)
- `is_active` (Boolean, default=True): Enable/disable sample without deletion

**11Labs Integration Fields**:
- `elevenlabs_voice_id` (String, Nullable): Generated voice ID from 11Labs API
  - Nullable until first successful clone attempt
  - Deterministic: same sample always generates same voice ID
  - Persisted for reuse across productions

**Metadata Fields**:
- `upload_date` (DateTime): Timestamp when sample was added
- `created_by` (String, Nullable): Admin who uploaded the sample
- `description` (String, Nullable): Notes about the sample (quality notes, version, etc.)

**Validation Rules**:
- `duration_seconds` must be between 30 and 600 (11Labs requirements)
- `source_format` must be in supported list: MP3, WAV, OGG, FLAC
- `sample_file_path` must be non-empty and valid MinIO path
- `character_id` must reference an existing character in database
- `is_active` determines whether sample can be used in production

**Lifecycle**:
```
Upload → Validate → Store in MinIO → Create DB record (elevenlabs_voice_id=NULL)
         → First Use → Call 11Labs API → Cache voice_id → Update DB record
         → Subsequent Uses → Use cached voice_id (no API call)
         → Disable/Delete → Set is_active=False (data preserved)
```

---

### 2. VoiceSynthesisConfig

Configuration for voice synthesis behavior, stored per-franchise or globally.

**Core Fields**:
- `id` (Integer, Primary Key): Unique identifier
- `franchise_id` (Integer, Foreign Key, Nullable): Applies to specific franchise (NULL = global default)
- `provider` (String, Enum): Voice provider choice
  - `"elevenlabs"`: Use 11Labs with stored voice samples
  - `"piper"`: Use Piper TTS (fallback default)

**11Labs-Specific Configuration**:
- `model_id` (String, default="eleven_monolingual_v1"): 11Labs model to use
- `voice_stability` (Float, default=0.5): Stability range [0.0, 1.0]
  - Lower = more variation in voice characteristics
  - Higher = more consistent, monotone delivery
- `similarity_boost` (Float, default=0.75): Similarity range [0.0, 1.0]
  - Lower = more creative synthesis, less faithful to sample
  - Higher = more accurate voice clone
- `use_speaker_boost` (Boolean, default=False): Enable speaker boost for audio quality

**Fallback Configuration**:
- `fallback_provider` (String, default="piper"): Provider to use if primary fails
- `enable_fallback_logging` (Boolean, default=True): Log fallback events for monitoring

**Metadata**:
- `created_at` (DateTime): When config was created
- `updated_at` (DateTime): Last modification timestamp
- `is_active` (Boolean, default=True): Can be disabled without deletion

**Validation Rules**:
- `voice_stability` and `similarity_boost` must be floats in [0.0, 1.0]
- `model_id` must be a valid 11Labs model identifier
- `provider` must be in supported list
- `fallback_provider` must differ from primary provider

---

## Schema: Database Migrations

### Migration: Add actor_voice_samples table

```python
# alembic/versions/001_add_actor_voice_samples.py

from alembic import op
import sqlalchemy as sa
from datetime import datetime

def upgrade():
    op.create_table(
        'actor_voice_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('character_name', sa.String(), nullable=False),
        sa.Column('sample_file_path', sa.String(), nullable=False),
        sa.Column('source_format', sa.String(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('elevenlabs_voice_id', sa.String(), nullable=True),
        sa.Column('upload_date', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_character_id', 'character_id'),
        sa.Index('idx_is_active', 'is_active'),
    )

def downgrade():
    op.drop_table('actor_voice_samples')
```

### Migration: Add voice_synthesis_config table

```python
# alembic/versions/002_add_voice_synthesis_config.py

def upgrade():
    op.create_table(
        'voice_synthesis_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('franchise_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model_id', sa.String(), default='eleven_monolingual_v1'),
        sa.Column('voice_stability', sa.Float(), default=0.5),
        sa.Column('similarity_boost', sa.Float(), default=0.75),
        sa.Column('use_speaker_boost', sa.Boolean(), default=False),
        sa.Column('fallback_provider', sa.String(), default='piper'),
        sa.Column('enable_fallback_logging', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.ForeignKeyConstraint(['franchise_id'], ['franchises.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_franchise_id', 'franchise_id'),
        sa.Index('idx_is_active', 'is_active'),
    )

def downgrade():
    op.drop_table('voice_synthesis_config')
```

---

## Entity Relationships

```
Character (existing)
    ↓ 1:N
ActorVoiceSample
    - Character has 0 or more voice samples
    - Each sample is for 1 character
    - Only 1 active sample per character (business rule)

Franchise (existing)
    ↓ 1:N
VoiceSynthesisConfig
    - Franchise has 1 global config (or NULL for system default)
    - Config determines provider behavior for that franchise

ActorVoiceSample → 11Labs API → voice_id (external)
    - Deterministic mapping (same sample = same voice_id)
    - Cached in-process and in DB
```

---

## Pydantic Schemas (Application Layer)

### ActorVoiceSampleSchema

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ActorVoiceSampleSchema(BaseModel):
    """Pydantic model for ActorVoiceSample entity."""
    
    id: int
    character_id: int
    character_name: str
    sample_file_path: str
    source_format: str = Field(
        ..., 
        description="Audio format: MP3, WAV, OGG, FLAC"
    )
    duration_seconds: float = Field(
        ..., 
        ge=30.0, 
        le=600.0,
        description="Duration must be 30-600 seconds"
    )
    elevenlabs_voice_id: Optional[str] = Field(
        None, 
        description="Voice ID from 11Labs API, generated on first use"
    )
    upload_date: datetime
    created_by: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True
```

### VoiceSynthesisConfigSchema

```python
class VoiceSynthesisConfigSchema(BaseModel):
    """Pydantic model for VoiceSynthesisConfig."""
    
    id: int
    franchise_id: Optional[int] = None
    provider: str = Field(
        ..., 
        pattern="^(elevenlabs|piper)$"
    )
    model_id: str = "eleven_monolingual_v1"
    voice_stability: float = Field(0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(0.75, ge=0.0, le=1.0)
    use_speaker_boost: bool = False
    fallback_provider: str = "piper"
    enable_fallback_logging: bool = True
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True
```

---

## State Transitions

### ActorVoiceSample Lifecycle

```
[Created]
   ↓
[Validated] (format, duration, quality checks)
   ↓
[Stored] (in MinIO + PostgreSQL, elevenlabs_voice_id=NULL)
   ↓
[First Production Use]
   ↓
[Voice ID Generated] (11Labs API call, cached, persisted)
   ↓
[Reused] (subsequent productions use cached voice_id)
   
OR (if disabled)
   ↓
[Disabled] (is_active=False, data preserved)
```

### VoiceSynthesisConfig Lifecycle

```
[Created] (franchise default or global)
   ↓
[Active] (used for production until changed)
   ↓
[Updated] (change provider settings, update timestamp)
   ↓
[Disabled] (is_active=False, fallback used instead)
```

---

## Key Constraints & Business Rules

1. **One Active Sample Per Character**: Only one ActorVoiceSample with `is_active=True` per character
   - Enforced at application layer (database constraint optional for future)
   - Allows safe replacement without data loss

2. **Voice ID Determinism**: Same ActorVoiceSample always generates the same voice_id
   - Enables caching and consistency across productions
   - 11Labs API responsibility

3. **Fallback Provider Consistency**: fallback_provider must differ from primary provider
   - Prevents configuration where primary and fallback are the same

4. **Duration Validation**: 30–600 seconds (11Labs API limits)
   - Enforced at Pydantic schema and database constraint

5. **Character Existence**: character_id must reference existing Character
   - Foreign key constraint in database

---

## Indexes for Performance

| Table | Column | Purpose |
|-------|--------|---------|
| actor_voice_samples | character_id | Query samples by character (fast lookup) |
| actor_voice_samples | is_active | Filter active samples (production queries) |
| voice_synthesis_config | franchise_id | Query config by franchise |
| voice_synthesis_config | is_active | Filter active configs |

---

## Data Retention & Cleanup

- **ActorVoiceSample**: Retained indefinitely unless manually disabled/deleted
  - Historical tracking via `upload_date` and `created_by`
  - Soft delete (is_active flag) preserves audit trail

- **VoiceSynthesisConfig**: Retained indefinitely
  - Historical tracking via `created_at` and `updated_at`
  - Allows rollback to previous configs if needed

- **MinIO Files**: Retained indefinitely unless franchise/character deleted
  - Can implement TTL policy if storage becomes an issue
