# Tasks: Golden Dataset Evaluation Framework

**Input**: Design documents from `specs/005-golden-dataset-eval/`  
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

## Format: `[ID] [P?] [SYNC/ASYNC] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[SYNC]**: Requires human review — prompt engineering, weight calibration, content authoring, DB migrations, integration assembly
- **[ASYNC]**: Can be delegated — mechanical Pydantic translation, scaffolding, test generation, aggregation math
- **[US#]**: User story this task belongs to (from spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create all new package directories and empty `__init__.py` files before any code is written.

- [x] T001 [ASYNC] Create package directories: `src/holodeck/evaluation/`, `src/holodeck/agents/evaluation/`, `tests/evals/fixtures/`, `tests/unit/evaluation/`
- [x] T002 [P] [ASYNC] Create `src/holodeck/evaluation/__init__.py` (empty)
- [x] T003 [P] [ASYNC] Create `src/holodeck/agents/evaluation/__init__.py` (empty)
- [x] T004 [P] [ASYNC] Create `tests/unit/evaluation/__init__.py` (empty)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schemas and database migration that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 [ASYNC] Implement all Pydantic v2 data models in `src/holodeck/evaluation/schemas.py`: `QualityGuidelines`, `ScopeBoundaries`, `GoldenDatasetEntry`, `DimensionScore` (with `weighted_score` computed property), `GuidelineComparison`, `EvaluationResult` (with `overall_score()` method), `EvaluationFailure`, `SummaryStatistics`, `BatchEvaluationReport` — translate directly from `specs/005-golden-dataset-eval/data-model.md`
- [x] T006 [SYNC] Add `EvaluationDimension.DIMENSIONS` class-level constant to `src/holodeck/evaluation/schemas.py` with all 8 dimensions (narrative_coherence=0.15, character_consistency=0.20, comedy_effectiveness=0.15, dialogue_naturalness=0.15, story_structure=0.10, emotional_impact=0.10, production_feasibility=0.10, thematic_alignment=0.05), including `signals`, `red_flags`, and `description` per dimension from `specs/005-golden-dataset-eval/data-model.md`; add `model_validator` asserting weights sum to exactly 1.0
- [x] T007 [P] [ASYNC] Write unit tests for `src/holodeck/evaluation/schemas.py` in `tests/unit/evaluation/test_schemas.py`: assert DIMENSIONS weights sum to 1.0, DimensionScore.weighted_score = score × weight, EvaluationResult.overall_score() = sum of weighted_scores, score/weight field constraints reject values outside [0.0, 1.0]
- [x] T008 [SYNC] Create Alembic migration for `evaluation_results` table in `alembic/versions/` using `uv run alembic revision --autogenerate -m "add evaluation_results table"`; review generated migration against `data-model.md` DB schema (columns: result_id UUID PK, script_id VARCHAR, golden_entry_id VARCHAR, overall_score FLOAT, passed_quality_gate BOOLEAN, red_flags_triggered JSONB, dimension_scores JSONB, guideline_comparison JSONB, previous_score FLOAT nullable, regression_detected BOOLEAN, evaluation_timestamp TIMESTAMPTZ); apply with `uv run alembic upgrade head`

**Checkpoint**: Schemas compile (`uv run mypy src/holodeck/evaluation/schemas.py`), T007 tests pass, migration applied.

---

## Phase 3: User Story 1 — Load and Curate Golden Dataset (Priority: P1) 🎯 MVP Start

**Goal**: Load, validate, and curate a golden dataset JSON file. Curate 5 Friends seed entries.

**Independent Test**: `uv run python tests/evals/script_eval.py --validate-only` succeeds and prints "5 entries validated" with no errors.

- [x] T009 [ASYNC] Implement `load_golden_dataset(path: Path) -> list[GoldenDatasetEntry]` and `validate_entry(entry: dict) -> ValidationResult` in `src/holodeck/evaluation/loader.py`: read JSON file, validate against Pydantic `GoldenDatasetEntry` schema, raise `ValueError` with field-level error details on malformed entries
- [x] T010 [P] [ASYNC] Write unit tests for `src/holodeck/evaluation/loader.py` in `tests/unit/evaluation/test_loader.py`: valid JSON loads 5 entries, missing required field raises ValueError with field name in message, empty entries list raises ValueError, malformed JSON raises ValueError, duplicate prompt_ids raises ValueError
- [x] T011 [ASYNC] Create `tests/evals/fixtures/friends_golden.json` JSON structure with 5 entries following `contracts/golden-dataset-schema.json`: prompt_ids = `rival-chef-s01`, `audition-callback-s01`, `dinosaur-date-s01`, `smelly-cat-recording-s01`, `the-break-argument-s01`; populate all required structural fields with placeholder guidelines
- [x] T012 [SYNC] Author full `quality_guidelines`, `scope_boundaries`, and `acceptable_variations` content for all 5 entries in `tests/evals/fixtures/friends_golden.json` using `specs/005-golden-dataset-eval/friends_bible.md` as reference; each entry must have: `narrative_goal`, `character_arcs` (dict), `comedy_approach`, `emotional_beats` (list ≥3), `production_constraints` (list ≥2), `thematic_focus`, `must_include` (list ≥2), `must_exclude` (list ≥1), `character_focus` (list), `acceptable_variations` (list ≥2)

**Checkpoint**: `uv run pytest tests/unit/evaluation/test_loader.py -xvs` passes; `load_golden_dataset("tests/evals/fixtures/friends_golden.json")` returns 5 `GoldenDatasetEntry` objects.

---

## Phase 4: User Story 2 — Generate Scripts with Golden Dataset Prompts (Priority: P1)

**Goal**: Given a golden dataset entry, invoke the Holodeck script generation pipeline and get back a script with a traceable `script_id`.

**Independent Test**: `EvaluationRunner.evaluate_single(entry, dry_run=True)` completes without error and returns a result stub with `golden_entry_id` set to the entry's `prompt_id`.

- [x] T013 [ASYNC] Create `JudgeAgent` scaffold in `src/holodeck/agents/evaluation/judge.py` following the exact `CriticAgent` pattern (`src/holodeck/agents/review/critic.py`): lazy-init `Agent`, `stage = StageType.REVIEW`, `__init__(model=None)`, `_get_agent()`, `validate_input(context)`, `process(context) -> AgentOutput`, `review_output(output) -> ReviewResult`, `@observe` decorators on `process` and `review_output`
- [x] T014 [SYNC] Implement `JudgeAgent.process()` system prompt and response parsing in `src/holodeck/agents/evaluation/judge.py`: inject `EvaluationDimension.DIMENSIONS` dict (description, weight, signals, red_flags) into system prompt; request JSON response with a `DimensionScore` object for each of the 8 dimensions; parse response into `list[DimensionScore]` with `reasoning` and `evidence`; store parsed scores in `AgentOutput.metadata["dimension_scores"]`

**Checkpoint**: `JudgeAgent` instantiates without error; `validate_input({"content": "script", "guidelines": {}})` returns `ValidationResult(valid=True)`.

---

## Phase 5: User Story 3 — Evaluate Scripts Against Quality Guidelines (Priority: P1)

**Goal**: End-to-end evaluation: golden entry → script generation → JudgeAgent scoring → `EvaluationResult` with all 8 dimension scores persisted to PostgreSQL.

**Independent Test**: `uv run pytest tests/unit/evaluation/test_runner.py -xvs` passes (no LLM calls); running `script_eval.py --entry rival-chef-s01` produces a JSON report with 8 dimension scores and `passed_quality_gate` field.

- [x] T015 [ASYNC] Write unit tests for `EvaluationRunner` in `tests/unit/evaluation/test_runner.py`: mock `JudgeAgent.process()` to return 8 `DimensionScore` objects; assert `EvaluationResult.dimension_scores` has exactly 8 items; assert `overall_score` equals weighted sum; assert `passed_quality_gate = overall_score >= 0.35`; assert `red_flags_triggered` list populated from triggered red flags
- [x] T016 [SYNC] Implement `EvaluationRunner.evaluate_single(entry: GoldenDatasetEntry, dry_run: bool = False) -> EvaluationResult` in `src/holodeck/evaluation/runner.py`: (1) invoke script generation pipeline with `entry.user_prompt`; (2) call `JudgeAgent.process()` with script content + guidelines; (3) parse `AgentOutput.metadata["dimension_scores"]` into `list[DimensionScore]`; (4) compute `overall_score` and `passed_quality_gate`; (5) collect `red_flags_triggered`; (6) persist `EvaluationResult` to PostgreSQL `evaluation_results` table; (7) return `EvaluationResult`
- [x] T017 [ASYNC] Implement `EvaluationRunner.get_history(golden_entry_id: str) -> list[EvaluationResult]` in `src/holodeck/evaluation/runner.py`: query `evaluation_results` table filtered by `golden_entry_id`, ordered by `evaluation_timestamp` DESC, return deserialized `EvaluationResult` list

**Checkpoint**: Unit tests pass; manual run `script_eval.py --entry rival-chef-s01` returns `EvaluationResult` with `dimension_scores` list of 8.

---

## Phase 6: User Story 4 — Compare Output to Expected Guidelines (Priority: P2)

**Goal**: Produce a `GuidelineComparison` showing which quality_guidelines requirements were met, partially met, or missed, with specific evidence from both the guidelines and the generated script.

**Independent Test**: `evaluate_single()` returns `EvaluationResult` where `guideline_comparison.met` + `guideline_comparison.partially_met` + `guideline_comparison.missed` covers all items from `quality_guidelines.must_include` and `emotional_beats`.

- [x] T018 [ASYNC] Implement guideline comparison logic in `src/holodeck/evaluation/runner.py` as `_compare_to_guidelines(script_content: str, entry: GoldenDatasetEntry, dimension_scores: list[DimensionScore]) -> GuidelineComparison`: for each item in `must_include`, `emotional_beats`, and `character_arcs`, check JudgeAgent evidence for match → classify as `met` / `partially_met` / `missed`; detect which `acceptable_variation` was used if any; populate `GuidelineComparison`
- [x] T019 [P] [ASYNC] Implement `BatchReporter.export_report(report: BatchEvaluationReport, output_dir: Path, formats: list[str]) -> dict[str, Path]` in `src/holodeck/evaluation/reporter.py`: serialize to JSON (`report.json`) and markdown (`report.md`) in `output_dir`; markdown report includes per-entry score table, dimension averages, and failures section

**Checkpoint**: `evaluate_single()` result has non-empty `guideline_comparison`; `export_report()` writes readable JSON and markdown files.

---

## Phase 7: User Story 5 — Batch Evaluate and Report Trends (Priority: P2)

**Goal**: Run evaluation on all golden dataset entries, skip failures, aggregate results into `BatchEvaluationReport` with summary statistics, and export.

**Independent Test**: `uv run python tests/evals/script_eval.py --all` completes even if one entry fails; summary prints pass/fail counts, average scores per dimension, and any failures with error messages.

- [x] T020 [ASYNC] Implement `EvaluationRunner.run_batch(entries: list[GoldenDatasetEntry]) -> BatchEvaluationReport` in `src/holodeck/evaluation/runner.py`: iterate entries, wrap `evaluate_single()` in `try/except Exception`, on failure append `EvaluationFailure(golden_entry_id, error_message, error_type, timestamp)`, always continue; assemble `BatchEvaluationReport` with results + failures at end
- [x] T021 [ASYNC] Implement `BatchReporter.aggregate(results: list[EvaluationResult], failures: list[EvaluationFailure]) -> SummaryStatistics` in `src/holodeck/evaluation/reporter.py`: compute total_entries, evaluated, failed, pass_count, fail_count, average_overall_score, average_score_by_dimension (dict per dimension name), regressions_detected count, common_red_flags (flags present in >50% of evaluations)
- [x] T022 [SYNC] Implement `tests/evals/script_eval.py` CLI entrypoint: `--entry <prompt_id>` runs single evaluation and prints JSON result; `--all` runs batch and prints summary; `--validate-only` loads golden dataset and validates structure without LLM calls; uses `typer` or `argparse`; exits with code 1 if any hard failures

**Checkpoint**: `script_eval.py --all` completes; `BatchEvaluationReport` contains correct `summary_statistics`.

---

## Phase 8: User Story 6 — Track Evaluation History and Regressions (Priority: P3)

**Goal**: Before persisting each `EvaluationResult`, query the most recent prior result for the same `golden_entry_id` and flag a regression if `overall_score` dropped >10%.

**Independent Test**: Run `script_eval.py --entry rival-chef-s01` twice; second result has `previous_score` set and `regression_detected=True` if score dropped; `get_history("rival-chef-s01")` returns 2 results ordered by timestamp.

- [x] T023 [SYNC] Implement regression detection in `EvaluationRunner.evaluate_single()` in `src/holodeck/evaluation/runner.py`: before persisting new result, query `evaluation_results` for most recent row with same `golden_entry_id` (order by `evaluation_timestamp` DESC, limit 1); if found: set `result.previous_score = prior.overall_score`; set `result.regression_detected = (prior.overall_score - result.overall_score) / prior.overall_score > 0.10`
- [x] T024 [ASYNC] Implement `BatchReporter.detect_regressions(report: BatchEvaluationReport) -> list[dict]` in `src/holodeck/evaluation/reporter.py`: filter `report.evaluation_results` where `regression_detected=True`; return list of dicts with `golden_entry_id`, `previous_score`, `current_score`, `delta_pct`; include in `export_report()` markdown output as "Regressions Detected" section

**Checkpoint**: `get_history()` returns 2+ results; second result has `regression_detected` field populated; regression section appears in batch markdown report.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Lint, type-check, schema validation, and end-to-end quickstart validation.

- [x] T025 [P] [ASYNC] Validate `tests/evals/fixtures/friends_golden.json` against `specs/005-golden-dataset-eval/contracts/golden-dataset-schema.json` using `jsonschema` or `pydantic`; fix any structural mismatches
- [x] T026 [P] [ASYNC] Run `uv run ruff check . && uv run ruff format .` and fix all lint/format errors in new evaluation modules (`src/holodeck/evaluation/`, `src/holodeck/agents/evaluation/`, `tests/unit/evaluation/`, `tests/evals/script_eval.py`)
- [x] T027 [P] [ASYNC] Run `uv run mypy .` and resolve all type errors in new evaluation modules; ensure all public function signatures have complete type hints
- [x] T028 [ASYNC] Run `uv run pytest tests/unit/evaluation/ -xvs` and confirm all unit tests pass with no LLM calls required
- [x] T029 [SYNC] Run `uv run python tests/evals/script_eval.py --validate-only` and confirm "5 entries validated" with no errors; confirm quickstart.md commands all execute correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately; T002/T003/T004 are parallel
- **Phase 2 (Foundational)**: Depends on Phase 1 — T005→T006→T007 (T007 and T008 are parallel after T005)
- **Phase 3 (US1)**: Depends on Phase 2 — T009/T011 parallel after T008; T012 SYNC after T011
- **Phase 4 (US2)**: Depends on Phase 2 — T013 parallel with Phase 3; T014 SYNC after T013
- **Phase 5 (US3)**: Depends on Phases 3 and 4 — T015 parallel with T016; T016 SYNC; T017 after T016
- **Phase 6 (US4)**: Depends on Phase 5 — T018 after T016; T019 parallel with T018
- **Phase 7 (US5)**: Depends on Phase 6 — T020 after T018; T021 after T020; T022 SYNC after T021
- **Phase 8 (US6)**: Depends on Phase 5 — T023 SYNC modifies evaluate_single(); T024 after T023
- **Phase 9 (Polish)**: Depends on all phases complete — T025/T026/T027 parallel; T028 after T027; T029 SYNC last

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|-----------|-----------------|
| US1 (Load Dataset) | Phase 2 complete | T008 migration applied |
| US2 (Generate Scripts) | Phase 2 complete | T008 migration applied (parallel with US1) |
| US3 (Evaluate Scripts) | US1 + US2 complete | T012 + T014 done |
| US4 (Compare to Guidelines) | US3 complete | T017 done |
| US5 (Batch Evaluate) | US4 complete | T019 done |
| US6 (History & Regression) | US3 complete | T017 done (parallel with US4/US5) |

### Parallel Opportunities

```bash
# Phase 1 — all in parallel:
T002, T003, T004

# Phase 2 — T007 and T008 parallel after T005:
T005 → T006 → [T007 ∥ T008]

# Phase 3 and Phase 4 — after Phase 2:
[US1: T009, T010, T011 → T012] ∥ [US2: T013 → T014]

# Phase 6 and US6 — after Phase 5:
[US4: T018, T019] ∥ [US6: T023 → T024]

# Phase 9 — polish tasks in parallel:
T025 ∥ T026 ∥ T027 → T028 → T029
```

---

## Implementation Strategy

### MVP (User Stories 1–3 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (schemas + migration)
3. Complete Phase 3: US1 — golden dataset loads and validates
4. Complete Phase 4: US2 — JudgeAgent created and prompted
5. Complete Phase 5: US3 — single evaluation runs end-to-end
6. **STOP and VALIDATE**: `script_eval.py --entry rival-chef-s01` returns EvaluationResult with 8 scores

### Incremental Delivery

1. MVP → `--validate-only` confirms dataset structure (Phase 3)
2. + US3 → `--entry` evaluates single script with full dimension scoring (Phase 5)
3. + US4 → guideline comparison in report (Phase 6)
4. + US5 → `--all` batch evaluation with summary stats (Phase 7)
5. + US6 → regression detection in batch report (Phase 8)

### Parallel Team Strategy

With two developers after Phase 2:
- **Dev A**: US1 (T009→T012) + US4 (T018→T019)
- **Dev B**: US2 (T013→T014) + US3 (T015→T017) + US5 (T020→T022)
- US6 (T023→T024) added when regression tracking is needed

---

## Notes

- `[P]` tasks touch different files — safe to run concurrently
- `[SYNC]` tasks: JudgeAgent prompt (T014), DIMENSIONS weights (T006), Friends content (T012), regression logic (T023), migration (T008), CLI entrypoint (T022) — all require human review
- `[ASYNC]` tasks: mechanical Pydantic translation, test scaffolding, aggregation math — delegate freely
- Constitution compliance: all new modules must have type hints, single responsibility, no god objects — verify with `mypy` at T027
- Commit after each phase checkpoint; use Conventional Commits (`feat(eval): ...`, `test(eval): ...`, `chore(eval): ...`)
