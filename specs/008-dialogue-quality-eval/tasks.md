# Tasks: Dialogue Quality Evaluation

**Input**: Design documents from `specs/008-dialogue-quality-eval/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Constitution note**: TDD enforced — test tasks written first; tests must FAIL before implementation begins.

## Format: `[ID] [P?] [SYNC/ASYNC] [Story?] Description`

- **[P]**: Can run in parallel with other [P] tasks
- **[SYNC]**: Requires human review (complex logic, LLM prompt design)
- **[ASYNC]**: Can be delegated (boilerplate, wiring, fixtures)
- **[Story]**: US1 = per-phrase scoring, US2 = scene scoring

---

## Phase 1: Setup

**Purpose**: Create package skeleton and test fixture directory.

- [ ] T001 [ASYNC] Create `src/holodeck/agents/dialogue_eval/__init__.py` (empty package marker)
- [ ] T002 [P] [ASYNC] Create `tests/unit/agents/dialogue_eval/__init__.py` (empty)
- [ ] T003 [P] [ASYNC] Create `tests/fixtures/dialogue/` directory with a `.gitkeep`

**Checkpoint**: Package structure exists; imports from `holodeck.agents.dialogue_eval` resolve.

---

## Phase 2: Foundational (Schemas — blocks both user stories)

**Purpose**: Define the shared Pydantic data contracts that both judges and the runner depend on.

**⚠️ CRITICAL**: Neither US1 nor US2 can be implemented until these schemas exist.

- [ ] T004 [SYNC] Implement `DimensionResult`, `LinePhraseScore`, `SceneScore`, and `GoldenConversationEntry` Pydantic v2 models in `src/holodeck/agents/dialogue_eval/schemas.py`

  Key rules from data-model.md:
  - `DimensionResult`: `score: int` (0–10), `reasoning: str`
  - `LinePhraseScore`: character, text, character_authenticity/dialogue_naturalness/comedy_contribution (each `DimensionResult`), `composite_score: float` as a **computed property** (weighted average: 0.4/0.35/0.25), not an LLM output
  - `SceneScore`: four `DimensionResult` fields (comedy_pacing/ensemble_dynamics/narrative_arc/thematic_coherence), `overall_score: float` as computed property (weights 0.30/0.30/0.25/0.15), `summary: str`, `line_count: int`
  - `GoldenConversationEntry`: prompt_id, user_prompt, description, expected_characters, quality_notes, dialogue (list of dicts with character/text/file keys)

- [ ] T005 [ASYNC] Write unit tests for schema validation in `tests/unit/agents/dialogue_eval/test_schemas.py`
  - Test composite_score computed correctly from dimension scores
  - Test overall_score computed correctly from scene dimensions
  - Test weights sum to 1.0 for both LinePhraseScore and SceneScore
  - Test score field rejects values outside 0–10

**Checkpoint**: `uv run pytest tests/unit/agents/dialogue_eval/test_schemas.py` — tests pass (schemas only, no LLM calls).

---

## Phase 3: User Story 1 — Per-Phrase Evaluation (Priority: P1) 🎯 MVP

**Goal**: Given a list of `{character, text}` pairs, return a `LinePhraseScore` for each line.

**Independent Test**: `uv run pytest tests/unit/agents/dialogue_eval/test_phrase_judge.py -v` passes using a stub LLM response (no real API call).

### Tests for User Story 1

> Write these tests FIRST — they must FAIL before T009.

- [ ] T006 [ASYNC] [US1] Write `tests/unit/agents/dialogue_eval/test_phrase_judge.py`
  - Test: valid JSON response from stub → produces correct `LinePhraseScore` with right composite
  - Test: unknown character (not in Friends roster) → character_authenticity is null, reasoning says "unknown character"
  - Test: LLM returns malformed JSON → raises `ValueError` with descriptive message
  - Test: empty text line → skipped or scored as 0 with "empty line" reasoning
  - Use `unittest.mock.patch` to stub the Agno agent `run()` call; do NOT make real LLM calls

### Implementation for User Story 1

- [ ] T007 [P] [ASYNC] [US1] Create `tests/fixtures/dialogue/friends_kitchen_argument.json` with a 6-line Rachel/Joey dialogue (character + text + empty file field). Include `prompt_id`, `description`, `expected_characters`, `quality_notes`, `dialogue` keys per data-model.md fixture format.

- [ ] T008 [SYNC] [US1] Implement `PhraseJudge` in `src/holodeck/agents/dialogue_eval/phrase_judge.py`

  Requirements:
  - Constructor: `__init__(self, model: Model | None = None)`
  - Method: `score(self, character: str, text: str) -> LinePhraseScore`
  - Uses `Agno Agent` with a system prompt that embeds all 6 Friends character profiles (from research.md character voice table): signals and red flags per character
  - Unknown characters: sets `character_authenticity` to `DimensionResult(score=0, reasoning="unknown character — authenticity not scored")`
  - LLM output format: JSON object with keys `character_authenticity`, `dialogue_naturalness`, `comedy_contribution` — each containing `score` (int) and `reasoning` (str)
  - Parses LLM JSON response into `LinePhraseScore`; raises `ValueError` on parse failure
  - Decorated with `@observe(name="phrase_judge.score", as_type="generation")` for Langfuse tracing

**Checkpoint**: T006 tests now PASS. `uv run pytest tests/unit/agents/dialogue_eval/test_phrase_judge.py`

---

## Phase 4: User Story 2 — Scene Scoring (Priority: P1)

**Goal**: Given the full ordered dialogue transcript, return one `SceneScore` with 4 dimensions and a summary.

**Independent Test**: `uv run pytest tests/unit/agents/dialogue_eval/test_scene_judge.py -v` passes using a stub.

### Tests for User Story 2

> Write these tests FIRST — they must FAIL before T011.

- [ ] T009 [ASYNC] [US2] Write `tests/unit/agents/dialogue_eval/test_scene_judge.py`
  - Test: valid 6-line transcript + stub JSON response → `SceneScore` with correct overall_score
  - Test: single-line transcript → scene returns `SceneScore` with summary noting "insufficient dialogue for ensemble dimensions"
  - Test: LLM returns malformed JSON → raises `ValueError`
  - Use `unittest.mock.patch` to stub Agno agent; no real LLM calls

### Implementation for User Story 2

- [ ] T010 [SYNC] [US2] Implement `SceneJudge` in `src/holodeck/agents/dialogue_eval/scene_judge.py`

  Requirements:
  - Constructor: `__init__(self, model: Model | None = None)`
  - Method: `score(self, lines: list[tuple[str, str]]) -> SceneScore` where each tuple is `(character, text)`
  - Single LLM call; sends full ordered transcript as a formatted block
  - If `len(lines) < 2`: returns `SceneScore` with all dimensions at score 5, summary "Insufficient dialogue for ensemble scoring", `line_count=len(lines)` — no LLM call
  - LLM output format: JSON with keys `comedy_pacing`, `ensemble_dynamics`, `narrative_arc`, `thematic_coherence` — each `{score, reasoning}` — plus `summary` string
  - `overall_score` computed by `SceneScore` model, not parsed from LLM
  - Decorated with `@observe(name="scene_judge.score", as_type="generation")`

- [ ] T011 [ASYNC] [US2] Implement `DialogueEvaluationRunner` in `src/holodeck/evaluation/dialogue_runner.py`

  Requirements:
  - Constructor: `__init__(self, model: Model | None = None)`
  - Lazy-initialises `PhraseJudge` and `SceneJudge` on first use
  - Method: `evaluate(self, dialogue: list[dict]) -> tuple[list[LinePhraseScore], SceneScore]`
    - Accepts the raw `dialogue_audio_metadata` structure: `[{character, text, file}, ...]`
    - Ignores `file` field
    - Calls `PhraseJudge.score()` sequentially for each line (max 50 lines; log warning and skip if exceeded)
    - Calls `SceneJudge.score()` once with all lines
    - Returns (line_scores, scene_score)
  - Method: `evaluate_fixture(self, fixture_path: str) -> tuple[list[LinePhraseScore], SceneScore]`
    - Loads JSON from path, validates as `GoldenConversationEntry`, calls `evaluate()`

- [ ] T012 [P] [ASYNC] [US2] Write `tests/unit/evaluation/test_dialogue_runner.py`
  - Test: runner calls phrase_judge N times and scene_judge once for N-line input
  - Test: `file` field in input dict is ignored (passes dict with junk file path, result unaffected)
  - Test: dialogue longer than 50 lines → runner processes only first 50, logs warning
  - Use `unittest.mock.Mock` for PhraseJudge and SceneJudge

**Checkpoint**: All unit tests pass. `uv run pytest tests/unit/agents/dialogue_eval/ tests/unit/evaluation/test_dialogue_runner.py`

---

## Phase 5: Polish & CLI

**Purpose**: Wire evaluation into the `holodeck` CLI; add golden fixtures; validate lint and types.

- [ ] T013 [ASYNC] Implement `src/holodeck/cli/dialogue_eval.py` — Typer sub-app with two commands:

  **`holodeck dialogue-eval run <path>`**
  - Loads JSON file at `<path>` (either raw `[{character, text, file}]` list OR a `GoldenConversationEntry` fixture)
  - Detects format: if top-level is a list → raw metadata; if dict with `dialogue` key → fixture
  - Runs `DialogueEvaluationRunner.evaluate()`
  - Prints per-line scores (character, text truncated to 50 chars, composite score, top failing dimension if composite < 6)
  - Prints scene score block (overall + 4 dimensions + summary)
  - Exits with code 1 if `overall_score < 5.0` (below quality bar)

  **`holodeck dialogue-eval batch`**
  - Discovers all `*.json` files under `tests/fixtures/dialogue/`
  - Runs `evaluate_fixture()` for each
  - Prints a Rich table: fixture name | overall_score | comedy_pacing | ensemble_dynamics | narrative_arc | thematic_coherence

- [ ] T014 [ASYNC] Register `dialogue_eval` sub-app in `src/holodeck/cli/main.py`
  - Add: `from holodeck.cli.dialogue_eval import app as dialogue_eval_app`
  - Add: `app.add_typer(dialogue_eval_app, name="dialogue-eval")`

- [ ] T015 [P] [ASYNC] Create 2 additional golden fixture files:
  - `tests/fixtures/dialogue/friends_emotional_beat.json` — a scene with Monica and Rachel having a sincere emotional moment (tests ensemble_dynamics and narrative_arc)
  - `tests/fixtures/dialogue/friends_joey_chandler_comedy.json` — a high-comedy scene between Joey and Chandler (tests comedy_pacing and character_authenticity)
  - Same JSON format as `friends_kitchen_argument.json` (6–8 lines each)

- [ ] T016 [ASYNC] Run `uv run ruff check . && uv run ruff format .` and fix any lint/format issues in new files

- [ ] T017 [ASYNC] Run `uv run mypy src/holodeck/agents/dialogue_eval/ src/holodeck/evaluation/dialogue_runner.py src/holodeck/cli/dialogue_eval.py` and fix all type errors

- [ ] T018 [ASYNC] Run full unit test suite `uv run pytest tests/unit/ -q` and confirm all pass (existing 263+ tests plus new ones)

**Checkpoint**: `holodeck dialogue-eval run tests/fixtures/dialogue/friends_kitchen_argument.json` prints per-phrase scores and a scene score. `holodeck dialogue-eval batch` prints a summary table for all 3 fixtures.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Schemas)**: Depends on Phase 1 — blocks Phases 3 and 4
- **Phase 3 (US1)**: Depends on Phase 2 — tests first (T006), then implementation (T007, T008)
- **Phase 4 (US2)**: Depends on Phase 2 — can start in parallel with Phase 3 after T004 is done
- **Phase 5 (Polish)**: Depends on Phases 3 and 4

### Within-Phase Parallelism

- T002, T003 can run in parallel with T001
- T007 (fixture) can run in parallel with T008 (phrase judge implementation)
- T012 (runner tests) can run in parallel with T015 (fixture files)
- T016, T017, T018 run sequentially (lint → types → tests)

---

## Implementation Strategy

### MVP (User Story 1 only — per-phrase scoring)

1. Phase 1: Setup (T001–T003)
2. Phase 2: Schemas (T004–T005)
3. Phase 3 tests first: T006 → confirm FAIL
4. Phase 3 impl: T007 + T008 → confirm T006 PASS
5. Smoke test: `uv run python -c "from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge; print('ok')"`
6. **STOP and validate** before adding scene scoring

### Full Delivery (both stories)

Continue with Phase 4 (T009–T012) then Phase 5 (T013–T018).

---

## Notes

- All judges are **synchronous** (matching existing `VoiceSynthesisAgent` pattern) even though Agno supports async — keeps the runner simple and avoids nested event-loop issues
- `file` field is accepted in input dicts but silently ignored throughout — do not add any validation or logging for it
- Fixture JSON files are also used as unit test inputs — keep them realistic (natural Friends dialogue) so SC-002/SC-003 success criteria are testable with real LLM calls
