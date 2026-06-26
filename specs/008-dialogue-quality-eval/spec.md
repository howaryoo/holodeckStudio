# Feature Specification: Dialogue Quality Evaluation

**Feature Branch**: `008-dialogue-quality-eval`
**Created**: 2026-06-26
**Status**: Draft
**Input**: Expand the golden dataset and evaluate the conversation itself — score each actor phrase and the overall scene, using the dialogue lines output (`=== DIALOGUE AUDIO ===`) as the evaluation target.

## Clarifications

### Session 2026-06-26

- Q: How should evaluation be triggered — standalone CLI only, auto after `produce` (always), or auto after `produce` with a flag? → A: Standalone CLI only (`holodeck dialogue-eval run <file>`); evaluation is always user-initiated and never runs automatically as part of `produce`.

## User Scenarios & Testing

### User Story 1 - Evaluate Individual Dialogue Lines (Priority: P1)

As a quality engineer, I want every dialogue line produced by the pipeline to receive a per-phrase score, so I can identify exactly which lines are weak (out of character, unnatural, unfunny) without reviewing the full audio.

**Why this priority**: Per-phrase scoring is the finest-grained signal. It pinpoints broken lines and drives targeted improvement of specific writers or prompts.

**Independent Test**: Can be fully tested by feeding a dialogue metadata list (character + text pairs, as produced by `=== DIALOGUE AUDIO ===`) into the evaluator and verifying a score and reasoning string is returned for every line, without needing video or audio files.

**Acceptance Scenarios**:

1. **Given** a completed production's dialogue metadata list, **When** the evaluator runs, **Then** each line receives a numeric score (0–10) and a brief reasoning note
2. **Given** a line that clearly breaks character (e.g., Joey using complex academic vocabulary), **When** scored, **Then** its character authenticity dimension scores below 4
3. **Given** an empty dialogue list, **When** evaluation runs, **Then** the evaluator reports zero lines evaluated with no error

---

### User Story 2 - Score the Overall Scene (Priority: P1)

As a showrunner, I want a single holistic score for each generated scene's dialogue, so I can compare episodes and identify which scenes need revision.

**Why this priority**: A per-line average alone misses scene-level properties (pacing, arc, ensemble dynamics). The overall score surfaces structural problems that line-by-line review misses.

**Independent Test**: Can be fully tested by submitting the full dialogue transcript of a scene and receiving one overall score with dimension breakdown and a summary — independent of per-phrase scoring.

**Acceptance Scenarios**:

1. **Given** a full scene transcript (ordered list of character + text), **When** evaluated holistically, **Then** the system returns an overall score (0–10), sub-scores for scene-level dimensions, and a one-paragraph summary
2. **Given** a scene where all lines are individually acceptable but the conversation lacks a comedic arc, **Then** the scene-level "comedy pacing" dimension scores low even if per-phrase scores are high
3. **Given** a scene evaluated twice (same input), **Then** scores are stable within ±1 point

---

### Edge Cases

- What happens when a character name in the dialogue is not a known Friends cast member? Evaluator must score it without character-specific expectations (fall back to generic dialogue quality).
- What if the dialogue list has only one line? Per-phrase scoring still works; scene-level dimensions that require multiple speakers report "insufficient dialogue."
- What if the LLM judge fails or times out for a line? That line is scored as null with a "judge unavailable" note; overall scene score excludes it and notes the gap.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST score each dialogue line individually across at least 3 per-phrase dimensions: character authenticity, dialogue naturalness, and comedy contribution
- **FR-002**: Each per-phrase score MUST be a numeric value on a 0–10 scale with an associated reasoning string of at least one sentence
- **FR-003**: The system MUST compute an overall scene score across at least 4 scene-level dimensions: comedy pacing, ensemble dynamics, narrative arc, and thematic coherence
- **FR-004**: Per-phrase and scene-level evaluation MUST be callable independently (scene evaluation does not require per-phrase to have run first)
- **FR-005**: Evaluation MUST accept the `dialogue_audio_metadata` structure (list of `{character, text, file}` dicts) as input; the `file` field is ignored (text-only)
- **FR-006**: The golden dataset MUST be expandable with new Friends-style conversation scenarios without code changes (data-driven JSON fixtures)
- **FR-007**: Batch evaluation across all golden fixture entries MUST be triggerable from the CLI and produce a printed summary

### Key Entities

- **LinePhraseScore**: Per-line result — character name, spoken text, dimension scores (character_authenticity, dialogue_naturalness, comedy_contribution), composite line score (0–10), reasoning
- **SceneScore**: Holistic result — overall score (0–10), dimension scores (comedy_pacing, ensemble_dynamics, narrative_arc, thematic_coherence), summary paragraph, line count
- **GoldenConversationEntry**: A golden fixture entry — prompt, description, expected character list, quality notes, and the dialogue list to evaluate

## Success Criteria

### Measurable Outcomes

- **SC-001**: A dialogue evaluation run (per-phrase + scene score) for a 10-line scene completes in under 60 seconds
- **SC-002**: Per-phrase scores correctly identify out-of-character lines with below-threshold scores in 80% of hand-crafted test cases
- **SC-003**: Scene-level scores correlate with human reviewer rankings (top-ranked scenes score higher than bottom-ranked scenes) in at least 70% of comparisons
- **SC-004**: Batch evaluation of 10 golden fixture entries completes in under 10 minutes

## Assumptions

- The Friends character roster (Rachel, Monica, Phoebe, Joey, Chandler, Ross) is the primary character set; the evaluator uses character-specific personality expectations for authenticity scoring
- Evaluation is LLM-as-judge (same model used for script generation); a separate model is not required
- MP3 audio quality evaluation is out of scope — text-only evaluation is the target (audio quality is covered by feature 007)
- Evaluation results are ephemeral (printed to terminal only); no database persistence in this phase
- The golden dataset for conversation scenarios is seeded with at least 3 Friends-style dialogue fixtures representing different scene types
- Scene coherence checking against the franchise Bible is out of scope; that remains with the Canon Historian agent
