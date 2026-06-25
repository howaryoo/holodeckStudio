# Implementation Plan: 11Labs Voice Clone Integration

**Branch**: `006-elevenlabs-voice-clone` | **Date**: 2026-06-25 | **Spec**: [spec.md](spec.md)  
**Input**: Integrate 11Labs Python API for voice cloning with actor voice samples in Franchise Bible

**Note**: This plan is filled in by the `/spec-plan` command. Phases 0–1 are executed here; Phase 2 (tasks.md) uses `/spec-tasks`.

## Summary

Integrate 11Labs Python API to enable voice cloning for character dialogue generation. Store actor voice samples in the Franchise Bible database; Voice Synthesis Agent will retrieve samples and use 11Labs API to generate character-specific audio. Start with 1 character (Rachel Green from Friends) to validate end-to-end flow; expand to other actors post-validation.

**Technical Approach**: 
- Add `ActorVoiceSample` entity to Franchise Bible schema
- Extend Voice Synthesis Agent to detect stored samples and route to 11Labs instead of Piper
- Implement 11Labs client wrapper with fallback to Piper on API failure
- Validate audio samples on upload (format, duration, quality)
- Cache generated voice IDs to avoid re-cloning the same sample

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: 
- `elevenlabs` Python SDK (11Labs API client)
- `pydantic` v2 (for data models)
- `sqlalchemy` (async ORM for Bible schema extension)
- `librosa` or `pydub` (audio validation and metadata extraction)

**Storage**: 
- PostgreSQL (Franchise Bible table for ActorVoiceSample metadata)
- MinIO (stored audio samples in `voice-samples/` prefix)
- In-process dict cache (voice ID → character mappings)

**Testing**: 
- Unit tests: Audio validation, voice ID caching, schema models
- Integration tests: 11Labs API client (with mock responses)
- E2E tests: Full production flow (upload sample → generate audio)

**Target Platform**: Linux server (Kubernetes via Colima)  
**Project Type**: Integrated feature in multi-agent production pipeline  
**Performance Goals**: 
- Voice synthesis latency < 10 seconds per 1000 characters
- Audio upload < 30 seconds (including validation)
- Support 100 concurrent voice synthesis requests

**Constraints**: 
- 11Labs API rate limits (pricing model TBD; assume <= 500 requests/minute for MVP)
- Audio sample duration 30 seconds to 10 minutes (11Labs limits)
- Voice ID generation must be deterministic per actor sample (enable caching)

**Scale/Scope**: 
- MVP: 1 character (Rachel Green) working end-to-end
- Phase 2: 5+ characters (other Friends cast) added without code changes
- Future: Multiple franchises with independent voice samples

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Compliance Assessment

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Python-First** | ✅ PASS | All code Python 3.11+; no external languages introduced |
| **II. Zen of Python** | ✅ PASS | Single obvious way: Voice Agent routes to 11Labs or Piper based on sample presence; explicit error handling (no silent fallbacks without logging) |
| **III. Single Responsibility** | ✅ PASS | New `ElevenLabsVoiceProvider` class handles 11Labs integration; Voice Agent delegates to provider; Bible storage is separate concern |
| **IV. Open/Closed** | ✅ PASS | New behavior added via `VoiceProvider` interface (protocol); existing Voice Agent remains closed to modification |
| **V. Dependency Inversion** | ✅ PASS | Voice Agent depends on `VoiceProvider` protocol, not concrete 11Labs client; abstractions (ActorVoiceSample, VoiceProvider) do not depend on implementation details |

**Gate Result**: ✅ **PASS** — All principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/006-elevenlabs-voice-clone/
├── plan.md              # This file (/spec-plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0: Research findings & decisions
├── data-model.md        # Phase 1: Data entities & database schema
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/           # Phase 1: API contracts
│   └── voice-provider.md
├── checklists/
│   └── requirements.md  # QA checklist
└── tasks.md             # Phase 2 output (/spec-tasks command)
```

### Source Code (repository root)

```text
src/holodeck/
├── agents/audio/
│   ├── voice_synthesis.py         # MODIFIED: Route to 11Labs or Piper
│   ├── providers/                 # NEW: Voice provider abstraction
│   │   ├── __init__.py
│   │   ├── base.py               # VoiceProvider protocol
│   │   ├── elevenlabs_provider.py # NEW: 11Labs integration
│   │   └── piper_provider.py      # REFACTORED: Extract from voice_synthesis
│   └── schemas/
│       ├── voice_sample.py        # NEW: ActorVoiceSample schema
│       └── voice_config.py        # MODIFIED: Add 11Labs config

├── memory/
│   └── franchise_bible.py         # MODIFIED: Add voice_samples table

├── storage/
│   └── bible_db.py               # MODIFIED: Voice sample persistence

tests/
├── unit/
│   ├── agents/audio/
│   │   ├── test_voice_synthesis.py          # MODIFIED
│   │   ├── test_elevenlabs_provider.py      # NEW
│   │   └── test_voice_validation.py         # NEW
│   └── storage/
│       └── test_bible_voice_samples.py      # NEW
├── integration/
│   ├── test_voice_synthesis_e2e.py          # NEW: Full flow with 11Labs mock
│   └── test_bible_voice_upload.py           # NEW: Upload & retrieval
└── evals/
    └── voice_quality_eval.py                # NEW: Voice similarity evaluation
```

**Structure Decision**: Integrate 11Labs voice cloning into existing voice synthesis pipeline with provider abstraction. Minimal changes to core Voice Agent; new `ElevenLabsVoiceProvider` handles 11Labs-specific logic. Bible schema extended for voice sample storage. Fallback to Piper provider remains default for characters without samples.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid model — SYNC for integration points and schema changes; ASYNC for provider implementation and tests.

### Preliminary Task Classification

| Task Category | [SYNC] Tasks | [ASYNC] Tasks | Rationale |
|---------------|------------|-----------|-----------|
| Data Operations | 2 | 1 | Schema extension (Franchise Bible) is SYNC (critical state change); voice sample validation utility is ASYNC |
| Integrations | 1 | 1 | 11Labs client wrapper + config is SYNC (external API); Piper provider refactor is ASYNC |
| Business Logic | 1 | 2 | Voice Agent routing logic (determining provider) is SYNC; individual provider implementations are ASYNC |
| Testing | 1 | 4 | Integration tests (E2E with real 11Labs mock) are SYNC; unit tests and evals are ASYNC |
| Infrastructure | 1 | 0 | Environment variable setup for ELEVENLABS_API_KEY is SYNC; no async infra needed |

**Total**: 6 SYNC tasks, 8 ASYNC tasks (Estimated 14 total tasks)

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications:**

- **Franchise Bible schema extension** (ActorVoiceSample table): Introduces persistent state; must be carefully designed to avoid migration issues and data loss
- **Voice Agent routing logic**: Determines which provider (11Labs or Piper) is used; incorrect logic could degrade voice quality for all productions
- **11Labs API integration point**: External API with rate limits and costs; needs careful error handling and fallback behavior
- **E2E test with real 11Labs mock**: Validates full flow; must be reviewed to ensure correctness before production use
- **Environment variable configuration**: ELEVENLABS_API_KEY security and ELEVENLABS_API_RATE_LIMIT tuning affect production stability

**Agent-Delegated [ASYNC] Classifications:**

- Individual provider implementations (ElevenLabsVoiceProvider, Piper refactor) — clear interface contracts
- Audio validation utility — testable in isolation
- Unit tests for providers and models — standard testing patterns
- Voice quality evaluation script — uses existing eval framework
- Documentation and quickstart guide — can be generated from design artifacts

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| Add ActorVoiceSample to Bible schema | SYNC | Persistent state, migration implications | High | Schema change affects all productions; must be human-reviewed |
| Implement Voice Agent routing logic | SYNC | Core business logic, affects all characters | High | Wrong routing could degrade quality for all users |
| 11Labs API client wrapper | SYNC | External API integration, error handling | High | API failures, rate limits, cost control critical |
| E2E test with 11Labs mock | SYNC | Validates full feature flow | High | Must confirm end-to-end correctness before production |
| Environment variable setup | SYNC | Security & rate limiting | Medium | API key handling and rate limit config affect stability |
| ElevenLabsVoiceProvider implementation | ASYNC | Clear contract, isolated concern | Low | Implements defined VoiceProvider interface |
| Piper provider extraction | ASYNC | Refactoring existing code, clear interface | Low | Existing code behavior unchanged, just reorganized |
| Audio validation utility | ASYNC | Isolated utility, standard patterns | Low | Can be tested independently |
| Unit tests for providers | ASYNC | Standard testing patterns | Low | Each provider tested against interface contract |
| Voice quality eval script | ASYNC | Uses existing eval framework | Low | Extends existing patterns |

## Complexity Tracking

> **No Constitution Check violations; no complexity justifications needed**
