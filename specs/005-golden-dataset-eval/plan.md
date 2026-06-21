# Implementation Plan: Golden Dataset Evaluation Framework

**Branch**: `001-holodeck-studio` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/005-golden-dataset-eval/spec.md`

## Summary

Build a golden dataset-based evaluation framework for sitcom script generation using "Friends" as the reference universe. The system curates 5 seed golden dataset entries, generates scripts via the existing Holodeck pipeline, and evaluates them through a new dedicated `JudgeAgent` across 8 quality dimensions. Results are persisted to PostgreSQL with regression detection (previous-run baseline). Batch evaluation is resilient: individual failures are skipped with clear reporting.

## Technical Context

**Language/Version**: Python 3.11+ (project standard)  
**Primary Dependencies**: agno ≥1.0.0 (JudgeAgent), pydantic ≥2.0 (schemas), SQLAlchemy 2.0 async + asyncpg (persistence), pytest + pytest-asyncio (tests), ruff + mypy strict (quality)  
**Storage**: PostgreSQL — new `evaluation_results` table (Alembic migration); golden dataset in JSON fixture files (no DB)  
**Testing**: pytest with `asyncio_mode = auto`; unit tests in `tests/unit/evaluation/`; eval scripts in `tests/evals/`  
**Target Platform**: Linux server (existing Colima/k8s dev environment)  
**Project Type**: Internal evaluation tool (not exposed via CLI in Phase 1)  
**Performance Goals**: Soft targets — ~2 min/script, ~30 min/10-entry batch (LLM inference latency is accepted bottleneck; optimize parallelization and caching where possible)  
**Constraints**: No GPU; LLM calls via Agno (routes to configured provider); batch evaluation is best-effort (resilient to individual failures)  
**Scale/Scope**: 5 seed golden dataset entries; designed to grow to 50+ without architectural changes

## Constitution Check

*GATE: Must pass before implementation begins.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First | ✅ Pass | All new code in Python 3.11+ |
| II. Zen of Python | ✅ Pass | Explicit schemas, no magic; single obvious way to load/evaluate/report |
| III. Single Responsibility | ✅ Pass | `loader.py` loads, `runner.py` orchestrates, `judge.py` scores, `reporter.py` aggregates — each one reason to change |
| IV. Open/Closed | ✅ Pass | New dimensions extend `DIMENSIONS` dict without modifying `JudgeAgent`; new reporters extend `BatchReporter` |
| V. Dependency Inversion | ✅ Pass | `EvaluationRunner` depends on `HolodeckAgentProtocol`, not concrete agents; `JudgeAgent` receives model as injection |
| Test-First | ✅ Pass | Unit tests defined before implementation tasks |
| Type hints | ✅ Pass | Required on all public function signatures |
| No god objects | ✅ Pass | No class handles more than one concern |

**Complexity justification**: None needed — all additions follow existing patterns with no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-golden-dataset-eval/
├── plan.md              # This file
├── research.md          # Phase 0: key decisions and rationale
├── data-model.md        # Phase 1: entities, fields, DB schema
├── quickstart.md        # Phase 1: how to run evaluations
├── friends_bible.md     # Reference: Friends franchise bible
├── contracts/
│   ├── golden-dataset-schema.json     # Input contract: golden dataset JSON
│   └── evaluation-result-schema.json  # Output contract: evaluation result JSON
└── tasks.md             # Phase 2 output (/spec-tasks command)
```

### Source Code (repository root)

```text
src/holodeck/
├── evaluation/                     # NEW — evaluation orchestration package
│   ├── __init__.py
│   ├── schemas.py                  # All Pydantic v2 models; DIMENSIONS class-level constant
│   ├── loader.py                   # load_golden_dataset(), validate_entry()
│   ├── runner.py                   # EvaluationRunner: evaluate_single(), run_batch(), get_history()
│   └── reporter.py                 # BatchReporter: aggregate(), detect_regressions(), export_report()
├── agents/
│   └── evaluation/                 # NEW — evaluation agent subpackage
│       ├── __init__.py
│       └── judge.py                # JudgeAgent (follows CriticAgent pattern)

tests/
├── evals/                          # NEW
│   ├── fixtures/
│   │   └── friends_golden.json     # 5 seed golden dataset entries
│   └── script_eval.py              # CLI entrypoint for eval runs (LLM-as-judge)
└── unit/
    └── evaluation/                 # NEW
        ├── __init__.py
        ├── test_schemas.py         # Pydantic model + DIMENSIONS weight sum tests
        ├── test_loader.py          # Load, validate, reject malformed entries
        └── test_runner.py          # EvaluationRunner unit tests (no LLM calls)
```

**Structure Decision**: Single-project layout extending the existing `src/holodeck/` tree. Evaluation is an internal concern; no separate service or CLI command added in Phase 1. New code slots into the established package hierarchy without restructuring.

## Triage Framework: [SYNC] vs [ASYNC] Classification

**Execution Strategy**: Hybrid. Schema and data model work is ASYNC-safe (mechanical, testable). Agent design and weight calibration require human judgment (SYNC).

### Preliminary Task Classification

| Task Category | [SYNC] Tasks | [ASYNC] Tasks | Rationale |
|---------------|-------------|--------------|-----------|
| Schemas & Models | 0 | 2 | Mechanical Pydantic v2 translation from data-model.md |
| Golden Dataset | 1 | 1 | Seed entry content requires human judgment; JSON structure is mechanical |
| JudgeAgent | 1 | 0 | System prompt and dimension weight calibration require human review |
| Loader & Validation | 0 | 1 | Straightforward validation logic with clear error cases |
| EvaluationRunner | 1 | 1 | Orchestration logic + regression detection require human review; persistence is mechanical |
| Reporter | 0 | 1 | Aggregation math is deterministic and testable |
| DB Migration | 1 | 0 | Schema changes to production DB require human oversight |
| Unit Tests | 0 | 3 | Test structure is well-defined; no architectural decisions |
| Eval Script | 1 | 0 | CLI entrypoint integrates all pieces; needs human integration review |

### Triage Decision Criteria Applied

**High-Risk [SYNC] Classifications**:
- `JudgeAgent` system prompt: Prompt engineering determines evaluation quality — wrong prompt = meaningless scores
- `DIMENSIONS` weights: Weights must sum to 1.0 and reflect meaningful priorities; calibration is an engineering judgment call
- `EvaluationRunner` regression detection: The >10% threshold logic and previous-run lookup must be correct; silent bugs here produce false regressions
- Alembic DB migration: Structural change to shared PostgreSQL instance
- `script_eval.py` integration: Ties all components together; integration errors surface here

**Agent-Delegated [ASYNC] Classifications**:
- Pydantic schema generation (translate data-model.md → Python code)
- `loader.py` validation logic (clear rules, testable)
- `reporter.py` aggregation math (deterministic)
- All unit test files (test structure is well-defined from spec)
- `friends_golden.json` JSON structure (schema-driven; only content is human-authored)

### Triage Audit Trail

| Task | Classification | Primary Criteria | Risk Level | Rationale |
|------|----------------|------------------|------------|-----------|
| `schemas.py` — Pydantic models | ASYNC | Mechanical translation | Low | Direct translation from data-model.md |
| `schemas.py` — DIMENSIONS dict + weights | SYNC | Calibration judgment | Medium | Weight values are engineering decisions affecting all scores |
| `friends_golden.json` — JSON structure | ASYNC | Schema-driven | Low | Validated against contract schema |
| `friends_golden.json` — entry content | SYNC | Content quality | High | Golden dataset quality determines evaluation validity |
| `judge.py` — JudgeAgent scaffold | ASYNC | Pattern follow | Low | Follows CriticAgent pattern exactly |
| `judge.py` — system prompt | SYNC | Prompt engineering | High | Determines dimension scoring quality |
| `loader.py` | ASYNC | Clear validation rules | Low | Validation rules fully specified |
| `runner.py` — batch orchestration | ASYNC | Standard async pattern | Low | error handling pattern is clear |
| `runner.py` — regression detection | SYNC | Correctness critical | Medium | Logic must be verified manually |
| `reporter.py` | ASYNC | Aggregation math | Low | Deterministic; testable |
| Alembic migration | SYNC | DB safety | High | Structural change; must be reviewed |
| `test_schemas.py` | ASYNC | Test structure known | Low | Weight sum, field constraints |
| `test_loader.py` | ASYNC | Test cases defined | Low | Load, validate, reject — clear cases |
| `test_runner.py` | ASYNC | Test cases defined | Low | Mock-free runner tests |
| `script_eval.py` | SYNC | Integration point | Medium | Assembles all components |

## Complexity Tracking

No constitution violations. No complexity justification required.
