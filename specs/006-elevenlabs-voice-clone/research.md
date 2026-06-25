# Research: 11Labs Voice Clone Integration

**Phase**: 0 — Research
**Date**: 2026-06-25
**Feature**: `006-elevenlabs-voice-clone`

---

## Decision 1: ElevenLabs Python SDK API

**Decision**: Use `elevenlabs>=1.0.0` (already declared in `pyproject.toml`) with the `ElevenLabs`
client class from `elevenlabs.client`.

**Verified API surface** (SDK ≥1.0.0):

```python
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

client = ElevenLabs(api_key="...")

# Clone voice from audio samples — returns a Voice object
voice = client.voices.add(
    name="Rachel Green",
    description="Rachel Green from Friends",
    files=["path/to/sample.mp3"],  # list of file paths (str or Path)
)
voice_id: str = voice.voice_id

# Synthesize speech — returns Iterator[bytes]
audio_chunks = client.text_to_speech.convert(
    voice_id=voice_id,
    text="That's not even a word!",
    model_id="eleven_monolingual_v1",
    voice_settings=VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        use_speaker_boost=False,
    ),
)
audio_bytes = b"".join(audio_chunks)  # collect and write to .mp3

# Delete a cloned voice (cleanup)
client.voices.delete(voice_id)
```

**Default free-tier model**: `"eleven_monolingual_v1"` (~10K chars/month).

**Rationale**: Official SDK with type-safe voice settings; already in requirements.

**Alternatives considered**: Raw `httpx` REST calls — rejected; verbose, manual auth headers, no type safety.

---

## Decision 2: Character Reference Strategy

**Decision**: `ActorVoiceSample` stores `bible_id` (UUID FK to `franchise_bibles.id`) and
`character_name` as a plain string. No FK to a `characters` table.

**Rationale**:
- Inspected `src/holodeck/storage/postgres.py`: the schema contains `franchise_bibles`,
  `bible_entries`, `productions`, `episodes`, `stages`, `assets` — **no `characters` table exists**.
- `VoiceSynthesisAgent.process()` already dispatches by character name string; a string key is
  sufficient for MVP lookup ("Rachel Green").
- A unique constraint on `(bible_id, character_name)` where `is_active=True` enforces the
  "one active sample per character" rule at the DB level without a FK to a missing table.

**Alternatives considered**:
- FK to `bible_entries.id` — rejected; BibleEntries can be deleted without cascade, creating
  orphaned voice samples; also requires character entries to exist before uploading samples.
- Create a new `characters` table — rejected; out of scope for this feature.

---

## Decision 3: VoiceSynthesisConfig Storage

**Decision**: Store voice synthesis configuration (model, stability, similarity_boost,
use_speaker_boost) as new fields in the existing `Settings` Pydantic model (`settings.py`),
backed by env vars. No database table.

**Rationale**:
- Inspected `src/holodeck/config/settings.py`: every tunable (model, quality gate, timeouts)
  already lives in `Settings`. Adding `elevenlabs_*` fields is consistent.
- Free-tier MVP needs one configuration set; per-franchise DB config adds zero behavioral value now.
- No migration, no repository, no CRUD — materially lower complexity.

**Alternatives considered**:
- Per-franchise DB table (`voice_synthesis_config`) — rejected; premature, requires 2 extra
  migration files and a full repository for config no one reads at MVP.
- JSONB on `franchise_bibles` — rejected; implicit and hard to validate with Pydantic.

---

## Decision 4: Primary Key Type

**Decision**: UUID primary keys (`PGUUID(as_uuid=True)`) for `actor_voice_samples`, consistent
with every existing ORM model in the project.

**Rationale**: Inspected `postgres.py`: `Production`, `FranchiseBible`, `BibleEntry`, `Episode`,
`Stage`, `Asset`, `Review`, `AgentExecution` — every table uses `UUID(as_uuid=True)`. Integer
auto-increment would be a jarring inconsistency.

**Alternatives considered**: Integer auto-increment — rejected; inconsistent with all other tables.

---

## Decision 5: Voice Provider Abstraction (Open/Closed compliance)

**Decision**: Introduce a `VoiceSynthesisProvider` `typing.Protocol` with:

```python
class VoiceSynthesisProvider(Protocol):
    async def synthesize(
        self, text: str, char_name: str, output_path: str, context: dict
    ) -> bool: ...
```

`ElevenLabsProvider` and `PiperProvider` are concrete implementations. `VoiceSynthesisAgent.process()`
selects provider at runtime by checking whether a voice sample exists for the character.

**Rationale**:
- Constitution IV (Open/Closed): adding a future provider (e.g., Google TTS) = new file, no
  changes to `voice_synthesis.py`.
- Constitution V (Dependency Inversion): `VoiceSynthesisAgent` depends on the Protocol abstraction,
  not on `ElevenLabs` concretely.
- Existing Piper synthesis helpers (`_synthesize_with_piper`, `_wav_to_mp3`) stay untouched;
  `PiperProvider` wraps them.

**Alternatives considered**:
- `if provider == "elevenlabs":` blocks inside `process()` — rejected; every new provider
  requires another branch, violating Open/Closed.
- Abstract base class — rejected; Protocol preferred per Constitution V ("prefer Protocol classes
  and composition over inheritance").

---

## Decision 6: Sample Duration Bounds

**Decision**: `ge=15.0, le=600.0` seconds. Minimum 15s; maximum 600s (10 min).

**Rationale**:
- Spec assumptions say 15–60s (MVP); FR-002 says 30s–10min.
- 15s minimum: aligns with ElevenLabs actual minimum (~5s, but 15s for quality) and the spec
  assumption's lower bound.
- 600s maximum: from FR-002, reserves headroom for longer studio recordings.
- Reconciliation: take spec assumption for minimum (15s) + FR-002 for maximum (600s).

**Alternatives considered**: 30–600s (FR-002 strict) — rejected; spec explicitly says 15s is
acceptable for MVP quality.

---

## Decision 7: Audio Sample Validation Tool

**Decision**: Use `ffprobe` (already a system dependency via `ffmpeg`) to extract audio metadata
for validation. Do **not** introduce `librosa` as a dependency.

**Rationale**:
- `ffmpeg` + `ffprobe` are already required system tools (see CLAUDE.md: "System dependencies:
  `ffmpeg`, `convert` (ImageMagick)").
- `librosa` is not in `pyproject.toml` and adds a large numpy/scipy dependency chain.
- `ffprobe -v error -show_entries format=duration,format_name` gives format + duration reliably.

**Alternatives considered**: `librosa.load()` — rejected; large dependency not already present.
`mutagen` — possible but `ffprobe` is already available system-wide with zero Python overhead.

---

## Decision 8: Alembic Migration Number

**Decision**: `003_add_actor_voice_samples.py` (`revision="003"`, `down_revision="002"`).

**Rationale**: Inspected `alembic/versions/`: existing migrations are `001` (initial schema)
and `002` (evaluation_results). This is the next in sequence.

---

## Decision 9: MinIO Storage Path

**Decision**: Store voice sample files under `voice-samples/{bible_id}/{char_slug}/sample.{ext}`
within the existing `holodeck-assets` bucket. `char_slug = character_name.lower().replace(" ", "_")`.

**Rationale**: Consistent with existing `media/{production_id}/` prefix convention. Per-bible
organization enables cascade cleanup when a franchise is deleted. Single bucket keeps MinIO simple.

**Alternatives considered**: Separate bucket — rejected; unnecessary bucket proliferation, existing
`object_store.py` client already targets `holodeck-assets`.

---

## Resolved Issues Summary

| Issue | Resolution |
|-------|-----------|
| No `characters` table | `bible_id` UUID FK to `franchise_bibles` + `character_name` string |
| Integer vs UUID PKs | UUID — matches every existing ORM table |
| Config: DB table vs Settings | `Settings` (env vars) — consistent with existing pattern |
| Duration bounds conflict (spec 15-60s vs FR-002 30s-10min) | `ge=15.0, le=600.0` |
| Provider abstraction | `VoiceSynthesisProvider` Protocol — Open/Closed + Dependency Inversion |
| ElevenLabs SDK API | `client.voices.add()` + `client.text_to_speech.convert()` |
| Audio validation tool | `ffprobe` (system dep already present); no `librosa` |
| Alembic migration number | `003` |
| MinIO bucket / prefix | `holodeck-assets` / `voice-samples/{bible_id}/{char_slug}/` |
