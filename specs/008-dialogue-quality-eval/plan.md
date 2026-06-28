# Implementation Plan: Dialogue Quality Evaluation

**Branch**: `008-dialogue-quality-eval` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/008-dialogue-quality-eval/spec.md`

## Summary

Add LLM-as-judge evaluation for generated dialogue conversations. Two scoring layers:
**per-phrase** (each dialogue line across character authenticity, naturalness, comedy contribution)
and **scene-level** (the full conversation across comedy pacing, ensemble dynamics, narrative arc,
thematic coherence). Input is the `dialogue_audio_metadata` list already produced by
`VoiceSynthesisAgent`; `file` paths are accepted but ignored — text-only evaluation, no audio
analysis. Results are persisted to PostgreSQL against golden dataset prompt IDs for regression
detection.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Agno (LLM-as-judge), Pydantic v2, Typer (CLI)
**Storage**: None — results are printed to terminal; golden fixtures are JSON files on disk
**Testing**: pytest with asyncio_mode=auto; unit tests with fixture dialogue lists, no DB or LLM calls
**Target Platform**: Linux server (same as holodeck pipeline)
**Project Type**: library + CLI extension
**Performance Goals**: 10-line scene evaluated in under 60 seconds (SC-001)
**Constraints**: Text-only — `file` field in metadata is IGNORED; no audio processing
**Scale/Scope**: 3+ golden conversation entries at launch; batch across all in single CLI run

## Constitution Check

*GATE: Must pass before implementation.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First | PASS | All code in Python 3.11+ |
| II. Zen of Python | PASS | One obvious path per concern; errors bubble explicitly |
| III. Single Responsibility | PASS | `agents/dialogue_eval/` is separate from `agents/evaluation/` (script-level); phrase judge and scene judge are separate classes |
| IV. Open/Closed | PASS | New `dialogue_eval/` module; existing `evaluation/` untouched |
| V. Dependency Inversion | PASS | Judges depend on Agno `Agent` abstraction; runner depends on judge protocols |

No violations. Complexity tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/008-dialogue-quality-eval/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/spec-tasks command)
```

### Source Code

```text
src/holodeck/
├── agents/
│   └── dialogue_eval/                   # NEW — dialogue-level LLM judges
│       ├── __init__.py
│       ├── schemas.py                   # LinePhraseScore, SceneScore, GoldenConversationEntry
│       ├── phrase_judge.py              # Per-line LLM judge
│       └── scene_judge.py              # Holistic scene LLM judge
├── evaluation/
│   └── dialogue_runner.py              # NEW — DialogueEvaluationRunner (orchestrates both judges)
├── cli/
│   └── dialogue_eval.py                # NEW — `holodeck dialogue-eval` sub-commands
│   └── main.py                         # MODIFY — register dialogue_eval app

tests/
├── fixtures/
│   └── dialogue/
│       └── friends_kitchen_argument.json    # NEW — fixture dialogue list for unit tests
├── unit/
│   └── agents/
│       └── dialogue_eval/
│           ├── test_phrase_judge.py         # NEW
│           └── test_scene_judge.py          # NEW
│   └── evaluation/
│       └── test_dialogue_runner.py          # NEW
```

**Structure Decision**: Extend the existing single-project layout under `src/holodeck/`. New
`agents/dialogue_eval/` sub-package is adjacent to (not merged into) existing `agents/evaluation/`
to preserve Single Responsibility. No storage layer — results are returned as Pydantic objects
and printed by the CLI.

## Triage Framework: [SYNC] vs [ASYNC] Classification

| Task Category | [SYNC] Tasks | [ASYNC] Tasks | Rationale |
|---------------|-------------|--------------|-----------|
| Schemas / Data Models | 1 | 0 | Pydantic models reviewed manually — they are the contract |
| LLM Judge Prompts | 2 | 0 | System prompts for character authenticity need careful character voice definitions |
| Evaluation Runner | 1 | 0 | Orchestration logic needs careful design |
| CLI Commands | 0 | 1 | Straightforward Typer extension following existing pattern |
| Tests | 0 | 3 | Fixture-based unit tests, no custom logic |

### High-Risk [SYNC] Classifications

- **Phrase judge system prompt** — must embed accurate Friends character voice profiles; wrong character expectations cause false-low authenticity scores
- **Scene judge dimensions** — comedy_pacing and ensemble_dynamics definitions must be specific enough to produce consistent, calibrated scores

### Agent-Delegated [ASYNC] Classifications

- **CLI command wiring** — `holodeck dialogue-eval run / batch` follows the existing Typer pattern
- **Unit test fixture files** — Friends kitchen argument dialogue fixture (character + text pairs)
- **Evaluation runner boilerplate** — calls phrase judge per line then scene judge; straightforward orchestration

## Phase 0: Research

### Decision: Per-Phrase Scoring Strategy

**Decision**: Call the LLM once per dialogue line (not batched), passing character name + text + character profile.

**Rationale**: Individual calls give clean per-line reasoning strings. Batching risks the LLM averaging scores or conflating lines. A 10-line scene = 10 LLM calls + 1 scene call = 11 total; at ~3s/call this is ~33 seconds, within SC-001 (60s).

**Alternative considered**: Batch all lines in one prompt. Rejected because response parsing is fragile when line count varies and reasoning quality degrades.

---

### Decision: Character Profile Injection

**Decision**: Embed Friends character profiles in the phrase judge system prompt as a static lookup (not from the franchise bible at runtime).

**Rationale**: The six core characters (Rachel, Monica, Phoebe, Joey, Chandler, Ross) are stable; injecting from the live bible adds latency and a runtime dependency. Character profiles are baked into the judge prompt:

| Character | Voice signature |
|-----------|----------------|
| Rachel | Emotional, fashion-focused, sarcastic when defensive; grew from spoiled to independent |
| Monica | Competitive, perfectionist, direct; chef vocabulary, nurturing |
| Phoebe | Quirky, spiritual, earnest; non-sequiturs, unusual beliefs |
| Joey | Simple, food-obsessed, charming; limited vocabulary, literal |
| Chandler | Sarcastic, self-deprecating; "could X BE any more Y?" pattern |
| Ross | Intellectual, nerdy; paleontology references, over-explains |

Unknown characters (not in this list) fall back to generic naturalness scoring without authenticity dimension.

---

### Decision: Scene-Level Scoring — Single LLM Call

**Decision**: One LLM call for the entire scene, receiving the full ordered transcript and returning 4 dimension scores.

**Rationale**: Scene-level properties (pacing, arc, ensemble dynamics) require the full context simultaneously. Attempting to derive them from aggregated per-line scores misses sequential properties (setup → punchline timing, turn-taking patterns).

**Alternative considered**: Average per-line scores for scene score. Rejected because per-line average cannot capture pacing or narrative arc.

---

### Decision: Text-Only Scope

**Decision**: Accept `dialogue_audio_metadata` structure (`[{character, text, file}]`) but read ONLY `character` and `text`. The `file` field is ignored throughout the evaluation pipeline.

**Rationale**: User constraint. Audio quality evaluation is covered by feature 007. Keeping evaluation text-only makes it fast, cheap (no audio loading), and testable with simple fixture JSON.

