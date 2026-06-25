# Tasks: 11Labs Voice Clone Integration

**Input**: Design documents from `specs/006-elevenlabs-voice-clone/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md
**Branch**: `006-elevenlabs-voice-clone`

---

## Format Guide

- **[ ]**: Not started | **[x]**: Complete
- **T###**: Task ID
- **[SYNC]**: Human review required (complex logic, external API, DB schema)
- **[ASYNC]**: Agent-delegatable (mechanical, well-specified, low-risk)
- **[P]**: Can run in parallel with other [P] tasks at same phase level

---

## Phase 1: Configuration & Environment

**Goal**: Extend `Settings` with ElevenLabs fields; update `.env.example`.

- [x] T001 [ASYNC] Extend `src/holodeck/config/settings.py` — add five new fields:
  `elevenlabs_api_key: str = ""`, `elevenlabs_voice_model: str = "eleven_monolingual_v1"`,
  `elevenlabs_voice_stability: float = 0.5`, `elevenlabs_similarity_boost: float = 0.75`,
  `elevenlabs_use_speaker_boost: bool = False`. All with `Field(description=...)`.

- [x] T002 [ASYNC] Update `.env.example` — add commented-out ElevenLabs block with all five
  vars from T001, one-line comment each explaining valid values.

**Checkpoint**: `Settings` loads ElevenLabs config from env; `.env.example` documents it.

---

## Phase 2: Database Schema

**Goal**: New `actor_voice_samples` table with UUID PK, FK to `franchise_bibles`, correct
constraints. Migration number 003.

- [x] T003 [SYNC] Create `alembic/versions/003_add_actor_voice_samples.py`:
  - `revision="003"`, `down_revision="002"`
  - Columns: `id UUID PK`, `bible_id UUID FK→franchise_bibles.id NOT NULL`,
    `character_name VARCHAR NOT NULL`, `sample_file_path VARCHAR NOT NULL`,
    `source_format VARCHAR NOT NULL`, `duration_seconds FLOAT NOT NULL`,
    `elevenlabs_voice_id VARCHAR NULL`, `upload_date DATETIME server_default=now()`,
    `created_by VARCHAR NULL`, `description VARCHAR NULL`,
    `is_active BOOLEAN NOT NULL server_default=true`
  - `CHECK (duration_seconds >= 15.0 AND duration_seconds <= 600.0)`
  - `CHECK (source_format IN ('mp3', 'wav', 'ogg', 'flac'))`
  - Index `ix_voice_samples_bible_char ON (bible_id, character_name)`
  - Index `ix_voice_samples_active ON (is_active)`
  - Partial unique index `uix_voice_samples_active_char ON (bible_id, character_name) WHERE is_active=true`
  - `downgrade()` drops all three indexes then the table

- [x] T004 [ASYNC] Add `ActorVoiceSample` ORM model to `src/holodeck/storage/postgres.py`:
  - `Mapped[UUID]` PK, `Mapped[UUID]` `bible_id` FK, all fields as `Mapped[str]` /
    `Mapped[float]` / `Mapped[bool]` / `Mapped[str | None]`
  - `relationship("FranchiseBible")` back-reference
  - Place after `BibleEntry` class in the same file

- [x] T005 [ASYNC] Add `ActorVoiceSampleRepository` to `src/holodeck/storage/postgres.py`:
  - `create(sample: ActorVoiceSample) -> ActorVoiceSample`
  - `get_active(bible_id: UUID, character_name: str) -> ActorVoiceSample | None`
    (queries where `is_active=True`, case-insensitive `character_name`)
  - `list_by_bible(bible_id: UUID) -> list[ActorVoiceSample]`
  - `update_voice_id(sample_id: UUID, voice_id: str) -> None`
  - `deactivate(bible_id: UUID, character_name: str) -> None`
    (sets `is_active=False` for matching active record)
  - All methods async, use `get_session()` context manager

**Checkpoint**: `uv run alembic upgrade head` creates the table; ORM model importable.

---

## Phase 3: Pydantic Schemas & MinIO Store

**Goal**: Pydantic v2 schemas for voice samples; MinIO upload/download helper.

- [x] T006 [ASYNC] Create `src/holodeck/agents/audio/schemas.py`:
  - `ActorVoiceSampleCreate(BaseModel)`: `bible_id: UUID`, `character_name: str`,
    `sample_file_path: str`, `source_format: str = Field(pattern=r"^(mp3|wav|ogg|flac)$")`,
    `duration_seconds: float = Field(ge=15.0, le=600.0)`, `created_by: str | None = None`,
    `description: str | None = None`
  - `ActorVoiceSample(BaseModel)`: same fields plus `id: UUID`, `elevenlabs_voice_id: str | None`,
    `upload_date: datetime`, `is_active: bool = True`
  - Use `model_config = ConfigDict(from_attributes=True)` (Pydantic v2, not `class Config`)

- [x] T007 [ASYNC] Create `src/holodeck/storage/voice_sample_store.py`:
  - `async def upload_voice_sample(file_path: str, bible_id: UUID, character_name: str) -> str`:
    reads local file, uploads to MinIO at `voice-samples/{bible_id}/{char_slug}/sample.{ext}`,
    returns the MinIO object path. Uses existing `object_store.py` client.
  - `async def validate_audio_file(file_path: str) -> tuple[float, str]`:
    runs `ffprobe -v error -show_entries format=duration,format_name` via `subprocess.run`,
    parses output, raises `ValueError` with descriptive message if duration out of [15, 600]
    or format not in `{mp3, wav, ogg, flac}`. Returns `(duration_seconds, format_name)`.

**Checkpoint**: Schemas importable; `validate_audio_file` rejects bad files correctly.

---

## Phase 4: Voice Provider Abstraction

**Goal**: `VoiceSynthesisProvider` Protocol; `PiperProvider` adapter; `ElevenLabsProvider`.

- [x] T008 [SYNC] Create `src/holodeck/agents/audio/voice_provider.py`:
  - `class VoiceSynthesisProvider(Protocol)`: single method
    `async def synthesize(self, text: str, char_name: str, output_path: str, context: dict) -> bool`
    annotated with `@runtime_checkable`
  - `class PiperProvider`: implements the Protocol by delegating to existing private helpers
    `_synthesize_with_piper()`, `_wav_to_mp3()`, `_get_piper_model_path()` from
    `voice_synthesis.py`. **Do not copy or modify those helpers** — import and call them.
  - Type-hint `PiperProvider` with `VoiceSynthesisProvider` in the return annotation.

- [x] T009 [SYNC] Create `src/holodeck/agents/audio/elevenlabs_provider.py`:
  - `class ElevenLabsProvider`: initialized with `settings: Settings` and
    `repository: ActorVoiceSampleRepository`, implements `VoiceSynthesisProvider` Protocol
  - `synthesize()`: looks up `ActorVoiceSample` for `(bible_id, char_name)` from context;
    if not found returns `False` (fallback trigger, not an error)
  - On first use: calls `client.voices.add(name=char_name, files=[sample_file_path])`,
    persists `voice_id` via `repository.update_voice_id()`
  - On subsequent use: reads `elevenlabs_voice_id` from DB, skips clone API call
  - Synthesis: `client.text_to_speech.convert(voice_id, text, model_id, VoiceSettings(...))`
  - Error handling: any `Exception` from ElevenLabs SDK → log `WARNING` with char name +
    exception message, return `False` so caller falls back to Piper
  - `bible_id` extracted from `context.get("bible_id")` — no fallback if missing (raise `KeyError`)

**Checkpoint**: `isinstance(ElevenLabsProvider(...), VoiceSynthesisProvider)` is `True`;
`isinstance(PiperProvider(), VoiceSynthesisProvider)` is `True`.

---

## Phase 5: Agent Refactor

**Goal**: `VoiceSynthesisAgent.process()` dispatches to ElevenLabs or Piper per character.
Must not break existing Piper-only behavior.

- [x] T010 [SYNC] Modify `src/holodeck/agents/audio/voice_synthesis.py`:
  - Add optional `providers: list[VoiceSynthesisProvider] | None = None` constructor arg.
    If `None`, default to `[PiperProvider()]` (existing behavior preserved, no regression).
  - In `process()`: for each `(char, text)` line, iterate providers in order. First provider
    that returns `True` wins; if all return `False`, produce no audio for that line (log warning).
  - Remove direct calls to `_synthesize_with_piper` from `process()` — those go through
    `PiperProvider.synthesize()` now.
  - Keep `_has_piper()`, `_has_gtts()`, `_parse_dialogue_lines()`, and all private helpers
    **unchanged** — `PiperProvider` wraps them.
  - `gTTS` fallback path stays as the last resort inside `PiperProvider.synthesize()` if
    Piper is unavailable.
  - All type hints on the new parameter and return types.

**Checkpoint**: Existing unit/integration tests still pass; agent works without API key (Piper only).

---

## Phase 6: CLI Sub-commands

**Goal**: `holodeck bible voice-sample add/list/disable` commands.

- [x] T011 [SYNC] Modify `src/holodeck/cli/main.py` — add `voice_sample_app` Typer sub-app
  mounted at `bible voice-sample`:
  - `add`: options `--bible TEXT` (bible ID), `--character TEXT`, `--file PATH`,
    `[--description TEXT]`. Flow: validate file via `validate_audio_file()`, upload to MinIO
    via `upload_voice_sample()`, deactivate any existing active sample for same character,
    create `ActorVoiceSample` DB record (voice_id=NULL), print confirmation.
  - `list`: option `--bible TEXT`. Queries `list_by_bible()`, prints table (character_name,
    upload_date, duration_seconds, is_active, elevenlabs_voice_id or "—").
  - `disable`: options `--bible TEXT`, `--character TEXT`. Calls `deactivate()`, prints confirmation.
  - All three commands use `asyncio.run()` entry point; all errors displayed via `console.print`
    with `[red]Error:[/red]` prefix (consistent with existing CLI style).

**Checkpoint**: `uv run holodeck bible voice-sample --help` works; `add` round-trip stores
a record and `list` shows it.

---

## Phase 7: Tests

**Goal**: Unit tests for provider Protocol conformance + ElevenLabs happy/fallback paths;
one integration smoke test.

- [x] T012 [P] [ASYNC] Create `tests/unit/agents/audio/test_voice_provider.py`:
  - `test_piper_provider_satisfies_protocol()` — `isinstance(PiperProvider(), VoiceSynthesisProvider)`
  - `test_elevenlabs_provider_satisfies_protocol()` — `isinstance(ElevenLabsProvider(...), VoiceSynthesisProvider)`
  - `test_voice_synthesis_agent_uses_piper_when_no_elevenlabs_key()` — instantiate agent
    with `PiperProvider()` only, call `process()` with a short script, assert audio files produced

- [x] T013 [P] [ASYNC] Create `tests/unit/agents/audio/test_elevenlabs_provider.py`:
  - `test_synthesize_returns_false_when_no_sample()` — no DB sample for character → returns `False`
  - `test_synthesize_calls_clone_on_first_use()` — mock `ElevenLabs` client, verify
    `voices.add()` called once, voice_id cached, `update_voice_id()` called
  - `test_synthesize_reuses_cached_voice_id()` — sample already has `elevenlabs_voice_id` in DB,
    verify `voices.add()` NOT called
  - `test_synthesize_returns_false_on_api_error()` — `client.text_to_speech.convert` raises,
    verify provider returns `False` (not raises), warning logged
  - Mock `ElevenLabs` client via `unittest.mock.patch`; mock `ActorVoiceSampleRepository`

- [x] T014 [SYNC] Create `tests/integration/test_voice_sample_flow.py`:
  - Requires k8s cluster + port-forwards (mark with `@pytest.mark.integration`)
  - `test_upload_sample_round_trip()`: upload a fixture MP3 → verify MinIO object exists →
    verify DB record created with correct fields → disable → verify `is_active=False`
  - `test_voice_synthesis_agent_with_elevenlabs_skipped_when_no_key()`: run agent with
    empty `elevenlabs_api_key`, verify Piper audio files produced (no ElevenLabs calls)
  - Fixture file: `tests/fixtures/audio/sample_15s.mp3` (15-second silent/test MP3)

**Checkpoint**: `uv run pytest tests/unit/ -x` passes; `uv run ruff check . && uv run mypy .` clean.

---

## Task Dependency Graph

```
T001 (Settings) → T002 (.env.example)
T003 (Migration) → T004 (ORM model) → T005 (Repository)
         ↓                               ↓
T006 (Pydantic schemas)           T007 (MinIO store)
         ↓                               ↓
T008 (Protocol + PiperProvider) ←───────┘
         ↓
T009 (ElevenLabsProvider) — depends on T005 (repo), T006 (schemas)
         ↓
T010 (Agent refactor) — depends on T008 + T009
         ↓
T011 (CLI) — depends on T005 + T007 + T010
         ↓
T012 + T013 (unit tests) — parallel, depend on T008 + T009
         ↓
T014 (integration test) — depends on T010 + T011
```

**Critical path**: T003 → T004 → T005 → T009 → T010 → T014

---

## Definition of Done

- [ ] `uv run alembic upgrade head` applies migration 003 cleanly
- [ ] `uv run holodeck bible voice-sample add --bible X --character "Rachel Green" --file sample.mp3` stores record
- [ ] `uv run holodeck produce "Rachel at Central Perk" --bible X` produces MP3s (ElevenLabs or Piper)
- [ ] `uv run pytest tests/unit/ -x` — all pass
- [ ] `uv run ruff check . && uv run ruff format --check .` — clean
- [ ] `uv run mypy .` — clean
