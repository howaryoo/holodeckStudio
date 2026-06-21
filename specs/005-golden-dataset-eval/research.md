# Research: Golden Dataset Evaluation Framework

## Decision 1: Evaluation Package Location

**Decision**: New top-level package `src/holodeck/evaluation/` (separate from `agents/`)  
**Rationale**: Evaluation is an orchestration concern that coordinates agents, schemas, and storage. Placing it under `agents/` would create a god-object; placing it as its own package follows Single Responsibility principle and mirrors the existing `pipeline/`, `memory/`, and `observability/` patterns.  
**Alternatives considered**:
- Under `agents/evaluation/`: Too narrow — the evaluation runner is not an agent; it coordinates agents
- Under `observability/`: Already exists with tracing/langfuse; eval adds distinct concerns (golden dataset, batch runs, regression)
- Under `pipeline/`: Pipeline is for production episode generation; eval is a testing/QA concern with different lifecycle

---

## Decision 2: Judge Agent Architecture

**Decision**: New `JudgeAgent` in `src/holodeck/agents/evaluation/judge.py`, following the exact same pattern as `CriticAgent` (lazy-init `Agent`, `@observe` decorator, `validate_input` / `process` / `review_output` methods, `StageType.REVIEW`)  
**Rationale**: Consistency with existing agent pattern. `CriticAgent` already does LLM-based narrative scoring and is the closest analog. Judge is distinct from Critic: Critic evaluates production-stage output; Judge evaluates against golden dataset guidelines with structured dimension scoring.  
**Alternatives considered**:
- Extend `CriticAgent`: Violated Open/Closed — would require modifying working code
- Standalone function: Loses `@observe` tracing, lazy-init model binding, and protocol compliance
- Reuse `CriticAgent` directly: Dimensions and prompt are fundamentally different; reuse would require runtime switching

---

## Decision 3: Golden Dataset Storage Format

**Decision**: JSON files in `tests/evals/fixtures/` (e.g., `friends_golden.json`), version-controlled in the repo  
**Rationale**: Follows existing project convention (`tests/evals/fixtures/rubric_golden.json` mentioned in CLAUDE.md). Human-authored, diffable, no database dependency for the dataset itself. Results are persisted to PostgreSQL; the dataset is static reference data.  
**Alternatives considered**:
- YAML: More human-friendly but adds parser dependency; JSON is already used in the project
- PostgreSQL table: Overkill for a small curated test set; dataset needs to be inspectable and version-controlled
- MinIO: Media storage; not appropriate for structured test fixtures

---

## Decision 4: Evaluation Schema Module

**Decision**: `src/holodeck/evaluation/schemas.py` — Pydantic v2 models for `GoldenDatasetEntry`, `EvaluationDimension` (class-level constant `DIMENSIONS` dict), `DimensionScore`, `EvaluationResult`, `BatchEvaluationReport`  
**Rationale**: Mirrors the `schemas/rubric.py` pattern from the Tech Pioneer course — class-level `DIMENSIONS` constant that gets injected into agent prompts. All models are Pydantic v2 with strict type hints. Keeps data contracts explicit and validated.  
**Alternatives considered**:
- TypedDict: Less validation; no field-level constraints
- dataclasses: No built-in validation; harder to serialize to JSON for reports

---

## Decision 5: Regression Baseline Implementation

**Decision**: `previous_score` field stored on `EvaluationResult` at write time. When a new evaluation is saved for a `golden_entry_id`, query the most recent prior result for the same entry ID and store its `overall_score` as `previous_score`. Regression triggered if `(previous_score - overall_score) / previous_score > 0.10`.  
**Rationale**: Simple, deterministic, matches user's clarification (previous run only). No need for a separate baseline table — the previous result is always the latest record before the current one.  
**Alternatives considered**:
- Rolling average: More robust but rejected by user; adds complexity (need min 3 samples)
- Separate baseline table: Redundant; the prior record is the baseline

---

## Decision 6: Batch Failure Handling Implementation

**Decision**: `EvaluationRunner.run_batch()` wraps each individual evaluation in `try/except`. Failed entries are captured as `EvaluationFailure` objects (containing `golden_entry_id`, `error_message`, `timestamp`) in `BatchEvaluationReport.failures`. Batch always completes.  
**Rationale**: Matches user's clarification (resilient, partial results). An `EvaluationFailure` record is distinct from an `EvaluationResult` so that downstream consumers can clearly differentiate "scored low" from "failed to evaluate".  
**Alternatives considered**:
- Raise on first failure: Rejected (fail-fast mode)
- Retry with backoff: Rejected (retry logic adds complexity; transient errors are uncommon in batch eval)

---

## Decision 7: Friends Golden Dataset Seed Entries

**Decision**: Ship 5 seed entries in `tests/evals/fixtures/friends_golden.json` covering the core evaluation dimensions:
1. **"The Rival Chef"** — Monica competition scenario (tests: Character Consistency, Comedy Effectiveness)
2. **"The Audition"** — Joey gets a life-changing callback (tests: Narrative Coherence, Story Structure, Emotional Impact)
3. **"The Dinosaur Date"** — Ross tries to impress a woman by talking about paleontology (tests: Dialogue Naturalness, Character Consistency)
4. **"The Smelly Cat Recording"** — Phoebe's song gets a professional production offer (tests: Thematic Alignment, Production Feasibility)
5. **"The Break Argument"** — Rachel confronts Ross about an old grievance (tests: Narrative Coherence, Emotional Impact, all dimensions holistically)

**Rationale**: 5 entries covers primary character-driven scenarios, each targeting different dimension clusters so batch evaluation provides diverse signals. Seed entries are complete with `quality_guidelines`, `acceptable_variations`, and `scope_boundaries`.  
**Alternatives considered**:
- 3 entries: Too few for meaningful trend analysis
- 10+ entries: High curation burden; start small and grow the dataset
