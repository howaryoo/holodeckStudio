# Implementation Plan: 11Labs Voice Clone Integration

**Branch**: `006-elevenlabs-voice-clone` | **Date**: 2026-06-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-elevenlabs-voice-clone/spec.md`

---

## Summary

Integrate the ElevenLabs Python SDK (`elevenlabs>=1.0.0`, already in `pyproject.toml`) into
`VoiceSynthesisAgent` to produce character-cloned audio during video production. Voice samples
are uploaded via a CLI sub-command (`holodeck bible voice-sample add`), stored in MinIO
under `voice-samples/{bible_id}/{char_slug}/`, and indexed in a new PostgreSQL table
`actor_voice_samples`. A `VoiceSynthesisProvider` Protocol abstracts the backend: ElevenLabs
is tried first; Piper TTS is the fallback. The MVP target is one character: Rachel Green
(Friends franchise).

---

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: `elevenlabs>=1.0.0` (SDK already declared), SQLAlchemy 2.0 async +
asyncpg, MinIO Python client, Pydantic v2, agno, Typer (CLI)
**Storage**: PostgreSQL — new `actor_voice_samples` table (UUID PK, FK to `franchise_bibles`);
MinIO — `holodeck-assets` bucket, `voice-samples/{bible_id}/{char_slug}/` prefix
**Testing**: pytest + `asyncio_mode=auto`; unit tests in `tests/unit/agents/audio/`;
integration tests in `tests/integration/` (require k8s cluster + port-forwards)
**Target Platform**: Linux server (same Colima/k8s stack)
**Project Type**: Pipeline extension — audio agent + new DB table + CLI sub-command
**Performance Goals**: < 15s voice synthesis per 1000 chars (ElevenLabs API on free tier);
< 30s file upload + validation for a 60s MP3
**Constraints**: 10K chars/month ElevenLabs free tier; zero paid plan; Piper fallback must
always succeed; cannot break existing `VoiceSynthesisAgent` behavior for non-cloned characters
**Scale/Scope**: MVP = 1 character (Rachel Green); pattern extendable to ~6 Friends characters
without code changes

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status | Notes |
|-----------|------|--------|-------|
| I. Python-First | All code in Python | ✅ PASS | No new language introduced |
| II. Zen of Python | Explicit provider selection; errors not silenced | ✅ PASS | Fallback logs a warning, not swallows silently |
| III. Single Responsibility | `ElevenLabsProvider` synthesizes; `VoiceSynthesisAgent` orchestrates | ✅ PASS | Each class has one reason to change |
| IV. Open/Closed | `VoiceSynthesisProvider` Protocol allows new providers without modifying `VoiceSynthesisAgent` | ✅ PASS | Verified by Protocol design |
| V. Dependency Inversion | `VoiceSynthesisAgent` depends on Protocol, not concrete `ElevenLabs` class | ✅ PASS | Confirmed in provider abstraction design |

**All gates pass. No violations to justify.**

---

## Project Structure

### Documentation (this feature)

```text
specs/006-elevenlabs-voice-clone/
├── plan.md              # This file
├── research.md          # Phase 0 output — all decisions resolved
├── data-model.md        # Phase 1 output — entities, ORM, migrations, schemas
├── quickstart.md        # Phase 1 output — developer setup guide
├── contracts/           # Phase 1 output — VoiceSynthesisProvider interface contract
└── tasks.md             # Phase 2 output (spec-tasks command)
```

### Source Code (repository root)

```text
src/holodeck/
├── agents/audio/
│   ├── voice_synthesis.py          # MODIFY: inject VoiceSynthesisProvider; dispatch per character
│   ├── voice_provider.py           # NEW: VoiceSynthesisProvider Protocol + PiperProvider adapter
│   └── elevenlabs_provider.py      # NEW: ElevenLabsProvider (clone + TTS + fallback)
├── agents/audio/schemas.py         # NEW: ActorVoiceSampleCreate, ActorVoiceSample Pydantic models
├── config/
│   └── settings.py                 # MODIFY: add elevenlabs_api_key, elevenlabs_voice_model, etc.
├── storage/
│   ├── postgres.py                 # MODIFY: add ActorVoiceSample ORM model + ActorVoiceSampleRepository
│   └── voice_sample_store.py       # NEW: MinIO upload/download for voice sample files
└── cli/
    └── main.py                     # MODIFY: add `holodeck bible voice-sample add/list/disable` commands

alembic/versions/
└── 003_add_actor_voice_samples.py  # NEW: Alembic migration

tests/
├── unit/agents/audio/
│   ├── test_elevenlabs_provider.py # NEW: unit tests (mocked ElevenLabs client)
│   └── test_voice_provider.py      # NEW: Protocol conformance tests
└── integration/
    └── test_voice_sample_flow.py   # NEW: upload → clone → synthesize (real MinIO + PG)
```

**Structure Decision**: Single project (existing layout). All changes are additive within
existing packages. No new top-level packages required.

---

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid — human-in-the-loop for external API integration and DB schema;
agent-delegated for scaffolding, Pydantic models, and unit test stubs.

### Preliminary Task Classification

| Task Category | [SYNC] Tasks | [ASYNC] Tasks | Rationale |
|---------------|-------------|--------------|-----------|
| DB Schema + Migration | 1 | 0 | Correctness-critical; FK + constraint decisions |
| ORM + Repository | 0 | 1 | Mechanical mapping of data-model.md |
| Pydantic Schemas | 0 | 1 | Direct translation from data-model.md |
| Settings Extension | 0 | 1 | Additive, well-defined fields |
| Voice Provider Protocol | 1 | 0 | Design choice (Protocol shape) has downstream impact |
| ElevenLabs Provider | 1 | 0 | External API auth, error handling, free-tier budget |
| Piper Provider Adapter | 0 | 1 | Wrap existing helpers without changes |
| Voice Synthesis Agent Refactor | 1 | 0 | Must not break existing Piper-only path |
| MinIO Voice Sample Store | 0 | 1 | Pattern clone of existing media_storage |
| CLI Sub-commands | 1 | 0 | UX decisions (argument names, error messages) |
| Unit Tests | 0 | 2 | Mechanical given Protocol contracts |
| Integration Test | 1 | 0 | Requires real infra understanding |
| Alembic Migration | 1 | 0 | Schema correctness, FK integrity |

### High-Risk [SYNC] Classifications

- **Alembic migration (003)**: Wrong FK or missing partial unique index causes data integrity
  issues in production.
- **ElevenLabs Provider**: External API key, rate limit budget (10K chars), error path design
  — must not silently drop audio.
- **VoiceSynthesisAgent refactor**: Must preserve existing behavior for Piper-only characters;
  regression risk.
- **CLI voice-sample commands**: Argument design affects admin workflow; hard to change post-ship.

### Agent-Delegated [ASYNC] Classifications

- ORM model and repository (direct translation of `data-model.md`)
- Pydantic schemas (direct translation of `data-model.md`)
- `Settings` extension (additive fields, well-specified)
- `PiperProvider` adapter (wraps existing helpers)
- `voice_sample_store.py` (clone of `media_storage.py` pattern)
- Unit test scaffolding for Protocol conformance

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk | Rationale |
|------|---------------|-----------------|------|-----------|
| Migration 003 | SYNC | Schema correctness | High | FK + partial unique index — wrong → silent data corruption |
| ORM ActorVoiceSample | ASYNC | Mechanical mapping | Low | data-model.md fully specifies every field |
| Pydantic schemas | ASYNC | Mechanical mapping | Low | data-model.md specifies fields + validators |
| Settings extension | ASYNC | Additive, specified | Low | Five new `Field(...)` entries, no logic |
| VoiceSynthesisProvider Protocol | SYNC | Interface design | Med | Method signature shapes all downstream code |
| ElevenLabsProvider | SYNC | External API, budget | High | Auth, 429 handling, free-tier char budget |
| PiperProvider adapter | ASYNC | Wrap existing | Low | Delegates to existing functions, no new logic |
| VoiceSynthesisAgent refactor | SYNC | Regression risk | High | Must not break Piper-only character path |
| voice_sample_store.py | ASYNC | Pattern clone | Low | MinIO upload pattern same as media_storage |
| CLI voice-sample add/list | SYNC | UX decisions | Med | Argument names + error messages are API surface |
| Unit tests | ASYNC | Mechanical given contracts | Low | Mock ElevenLabs client |
| Integration test | SYNC | Real infra | Med | Needs k8s + port-forwards understanding |

---

## Complexity Tracking

> No Constitution violations found. This section intentionally omitted.
