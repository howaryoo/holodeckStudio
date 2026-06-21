# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All Python invocations must go through `uv run` — never assume a global Python or an activated venv.

```bash
uv sync                                    # install / sync dependencies into .venv/
uv run pytest tests/unit/                  # run unit tests (no external services required)
uv run pytest tests/integration/           # run integration tests (requires k8s cluster + port-forwards)
uv run pytest tests/ -k test_name          # run a single test by name
uv run pytest --cov=holodeck --cov-report=html  # run with coverage report
uv run ruff check . && uv run ruff format .     # lint + format (line-length=100)
uv run mypy .                              # strict type-check
```

All tests must pass and type-checking must be clean before code review.

## Infrastructure

The system runs on **Kubernetes via Colima** with PostgreSQL, MinIO, and optional Langfuse observability.

```bash
make start          # Full cluster up: colima → k8s → infra → migrations
make stop           # Stop services (cluster still running, data preserved)
make delete         # Full teardown including volumes (⚠ destroys all data)
make status         # Check cluster + k8s pod status
```

On startup, `make start` sets up port-forwards to PostgreSQL (5432), MinIO API (9000), MinIO Console (9001), and runs `alembic upgrade head` for migrations.

For unit tests that don't touch storage, you don't need the cluster.

## Environment Setup

```bash
cp .env.example .env
# Fill in:
# - DATABASE_URL (provided by make start on localhost:5432)
# - MINIO_* (provided by make start on localhost:9000)
# - HOLODECK_DEFAULT_MODEL=<provider/model_id> (e.g., openai/gpt-4o, anthropic/claude-opus-4-1)
# - Optional: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
# - Optional: Langfuse credentials for observability
```

Model providers are abstracted via **Agno**; env var precedence is CLI flag > config file > `.env` > defaults.

## Architecture

### High-Level Design

**Holodeck Studio** is a multi-agent pipeline that transforms a user prompt into a complete video episode:

```
User Prompt
    ↓
Showrunner Agent (concept → outline)
    ↓
Head Writer Agent (outline → detailed script with dialogue)
    ↓
Staff Writer Agent (refine script, add stage directions)
    ↓
[Each agent can iterate via ReviewCycle: process → self-review → approve/revise]
    ↓
Production Pipeline:
    ├─ Character Designer Agent
    ├─ Frame Renderer Agent (with lip-sync, multi-character support)
    ├─ Voice Synthesis Agent (Piper TTS + gTTS fallback, multi-voice casting)
    ├─ Video Assembler Agent (color grading, camera moves, zoom, smooth transitions)
    └─ Canon Historian Agent (verify against franchise bible entries)
    ↓
Critic Agent (final quality review)
    ↓
Video Output (MP4) + frames + audio tracks
```

### Package Structure

```
src/holodeck/
├── agents/              # Agent implementations by role
│   ├── base.py         # Agent base class (@observe decorator pattern)
│   ├── showrunner.py   # Concept/outline generation
│   ├── producer.py     # Production orchestration + quality gates
│   ├── writers/        # Head Writer, Staff Writer implementations
│   ├── design/         # Character Designer
│   ├── directing/      # Director/Canon Historian
│   ├── video/          # Video rendering (frame_renderer, video_assembler, etc.)
│   ├── audio/          # Voice synthesis (TTS integration, multi-voice)
│   ├── production/     # Production-stage agents
│   └── review/         # Critic agent
├── cli/                # Typer CLI entry points (produce, bible, config, status commands)
├── pipeline/           # Orchestration engine
│   ├── orchestrator.py # PipelineOrchestrator: manages agent flow
│   ├── runner.py       # PipelineRunner: executes stages, manages state
│   ├── events.py       # Event emission for observability
│   └── stages.py       # Stage definitions + callbacks
├── memory/             # In-process state: Franchise Bible, Episode, Production
├── storage/            # PostgreSQL (SQLAlchemy ORM) + MinIO (S3 API) adapters
├── config/             # Pydantic Settings for env-based configuration
├── observability/      # Langfuse tracing + LLM-as-judge evals
└── cache.py           # In-memory/Redis caching for LLM outputs
```

### Core Abstractions

**Agent Base Class** (`agents/base.py`):
- All agents inherit from a base class
- Decorated with `@observe` for Langfuse tracing
- Implement `process(context)` and optional `review_output(context, output)` methods
- `context` is a dict passed between agents (script, characters, scene descriptions, etc.)
- Each agent can iterate: process → self-review → approve/reject → revise

**Pipeline Runner** (`pipeline/runner.py`):
- Executes agents in sequence or parallel stages
- Manages context flow between agents
- Emits events (via `pipeline/events.py`) for logging + Langfuse
- Handles approval checkpoints (interactive approval or auto-approve based on quality gates)
- Supports "dry-run" mode (validate prompts without LLM calls)

**Franchise Bible** (`memory/`):
- In-memory store for canonical lore (characters, locations, technology, events)
- Populated via CLI: `holodeck bible create`, `holodeck bible add-entry`, `holodeck bible search`
- Injected as context for Canon Historian to verify consistency
- Lives for the process lifetime (not persisted)

### Media Generation

- **Frames**: SVG-based character silhouettes (rendered via `frame_renderer.py` → ImageMagick)
- **Audio**: Piper TTS (CPU-optimized, models in `piper_models/`) with gTTS fallback
- **Video**: FFmpeg with:
  - Two-pass zoom (raw 24fps → zoompan filter for smooth motion)
  - Color grading presets (warm, cool, sepia, noir, vivid, neutral)
  - Camera moves (dolly, pan, tilt)
  - Multi-character frames (center + side listener)
  - Lip-sync approximation (frame-count-based mouth toggle)
  - Preview mode (640x360, 15-frame cap, 12 FPS)

System dependencies: `ffmpeg`, `convert` (ImageMagick), `piper-tts` (Python package, ONNX CPU).

## Key Conventions

### Pydantic & Type Hints
- **Pydantic v2** for all data models (`BaseModel`, `Field`, `model_validator`, `ConfigDict`)
- Type hints required on all public functions and method signatures
- Async-first for all I/O paths; `asyncio.run()` only at CLI entry points

### Testing
- **Unit tests** in `tests/unit/` (no external services)
- **Integration tests** in `tests/integration/` (requires k8s cluster + port-forwards)
- **E2E tests** in `tests/e2e/` (shell scripts for smoke tests)
- **No mocks in integration/e2E tests** — use real services
- Pytest runs with `asyncio_mode = auto`

### Code Style
- Ruff for linting + formatting; mypy strict mode for type-checking
- No commented-out placeholder code — use `TODO(<name>): <what>` instead
- Line length: 100 characters
- `structlog` for logging (once observability is fully configured)

### Agno Agent Pattern
All agents follow the same shape:

```python
from agno.agent import Agent
from holodeck.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="my-agent",
            description="What this agent does",
            model="defaults to HOLODECK_DEFAULT_MODEL env var"
        )
    
    async def process(self, context: dict) -> dict:
        # Perform work, update context
        return context
    
    async def review_output(self, context: dict, output: dict) -> bool:
        # Optional: self-review logic
        return True  # approve
```

The `@observe` decorator (from `observability/`) wraps process/review_output for Langfuse tracing.

## Database & Storage

**PostgreSQL** (via SQLAlchemy ORM, async with asyncpg):
- Migrations managed by Alembic
- Run `alembic upgrade head` after pulling schema changes
- Tables for productions, episodes, scripts, characters, evaluation logs

**MinIO** (S3-compatible):
- Stores generated frames, audio, videos
- Default bucket: configured in `.env` (MINIO_BUCKET)
- Client initialized in `storage/minio_client.py`

**Redis** (optional):
- For distributed caching across replicas
- Falls back to in-memory cache if Redis unavailable

## Observability

**Langfuse** (optional, controlled via `.env`):
- Automatic LLM call tracing via `openinference-instrumentation-agno`
- Custom event emission via `pipeline/events.py` → Langfuse
- Evaluation evals framework for quality gates

Disable Langfuse by leaving credentials blank in `.env`.

## Running the CLI

```bash
# Dry-run: validate prompt without LLM calls
uv run holodeck produce "A stranded crew discovers an ancient relay network" --dry-run

# Full production: all 5 agents + media generation
uv run holodeck produce "A stranded crew..." --bible <bible-id>

# Production modes: supervised (approve each agent), autonomous (no approvals)
uv run holodeck produce "..." --mode supervised
uv run holodeck produce "..." --no-approve

# Status and configuration
uv run holodeck status <production-id> --verbose
uv run holodeck config show
uv run holodeck config set holodeck_default_model "openai/gpt-4o"
```

## Common Tasks

### Adding a New Agent

1. Create file in `src/holodeck/agents/<department>/new_agent.py`
2. Inherit from `BaseAgent`; implement `process()` and optional `review_output()`
3. Add to pipeline in `pipeline/runner.py` (register in stage definitions or orchestrator)
4. Wire into CLI if user-facing
5. Add unit tests in `tests/unit/agents/<department>/`

### Modifying a Data Model

1. Update Pydantic model in `src/holodeck/agents/<agent>/schemas.py` or equivalent
2. If database-backed, create Alembic migration: `uv run alembic revision --autogenerate -m "reason"`
3. Review migration, then apply: `uv run alembic upgrade head`
4. Update type hints in agents that consume/produce this model

### Debugging an Agent

1. Run in dry-run mode first: `uv run holodeck produce "..." --dry-run`
2. Add print/logging to agent's `process()` method
3. For Langfuse-traced runs, check the Langfuse dashboard at http://localhost:3000
4. Unit test the agent in isolation: `uv run pytest tests/unit/agents/<dept>/test_<agent>.py -xvs`

### Extending Media Generation

- **Color grading presets**: Edit `src/holodeck/agents/video/video_assembler.py` (`_COLOR_PRESETS` dict)
- **Character SVG rendering**: Extend `src/holodeck/agents/video/character_renderer.py` (face, clothing, hair, accessories)
- **Camera moves**: Add to `CameraMove` enum and `_build_camera_move_filter()` in `video_assembler.py`
- **TTS voices**: Add models to `piper_models/`, update `_DEFAULT_PIPER_MODELS` mapping in `voice_synthesis.py`

## Dependencies & Constraints

- **Python 3.11+** (not 3.10 or earlier)
- **Agno ≥1.0.0** for agent framework (abstracts OpenAI, Anthropic, Google)
- **SQLAlchemy ≥2.0 (async)** with **asyncpg** for PostgreSQL
- **MinIO ≥7.0** for S3-compatible object storage
- **Pydantic ≥2.0** (strictly v2, not v1)
- **FFmpeg** + **ImageMagick** for media generation
- **Piper TTS ≥1.4.2** (Python package, CPU-based ONNX inference)

No GPU required; all inference is CPU-bound (via Piper ONNX, Agno delegates to remote LLM APIs).

## Useful References

- **AGENTS.md**: Session summary with task progress and known issues
- **specs/**: Specification documents for each phase (module/sprint)
- **Langfuse**: http://localhost:3000 (when running, MinIO Console: http://localhost:9001)
- **Git**: Commits follow Conventional Commits (`feat/fix/test/refactor/docs/chore`)

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at specs/005-golden-dataset-eval/plan.md
<!-- SPECKIT END -->
