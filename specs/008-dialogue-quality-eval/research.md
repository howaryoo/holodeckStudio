# Research: Dialogue Quality Evaluation

**Branch**: `008-dialogue-quality-eval` | **Date**: 2026-06-26

All decisions consolidated from plan.md Phase 0 research.

## LLM-as-Judge for Dialogue

**Decision**: Use Agno `Agent` with structured JSON output for both phrase-level and scene-level scoring, matching the existing `JudgeAgent` pattern in `agents/evaluation/judge.py`.

**Rationale**: The existing pattern is proven (feature 005), avoids introducing new dependencies, and integrates with Langfuse tracing via `@observe` decorator automatically.

**Alternatives considered**:
- Dedicated evaluation model (GPT-4o-mini): rejected — adds provider config complexity with no quality benefit over the configured default model
- Rule-based scoring: rejected — too brittle for nuanced properties like character voice or comedy timing

## Per-Phrase Scoring

**Decision**: One LLM call per dialogue line; 3 dimensions scored per line (0–10 scale, integer); JSON array response.

**Dimensions**:
- `character_authenticity` (weight 0.4): Does this line sound like this specific character?
- `dialogue_naturalness` (weight 0.35): Is this a line a human actor could deliver naturally?
- `comedy_contribution` (weight 0.25): Does this line land a joke, build to one, or pay one off?

**Score schema**:
```json
{
  "character": "JOEY",
  "text": "Could you BE any more complicated?",
  "character_authenticity": {"score": 3, "reasoning": "This is Chandler's catchphrase, not Joey's voice"},
  "dialogue_naturalness": {"score": 8, "reasoning": "The line flows naturally when spoken"},
  "comedy_contribution": {"score": 7, "reasoning": "Funny line, though misattributed"},
  "composite_score": 5.45
}
```

## Scene-Level Scoring

**Decision**: One LLM call receiving the full ordered transcript; 4 dimensions; 0–10 integer scores.

**Dimensions**:
- `comedy_pacing` (weight 0.30): Are jokes well-timed? Is there rhythm of setup → punchline across the scene?
- `ensemble_dynamics` (weight 0.30): Does the conversation reflect real character relationships and interactions?
- `narrative_arc` (weight 0.25): Does the scene have a beginning, middle, end — a small story?
- `thematic_coherence` (weight 0.15): Does the scene feel like it belongs to the same episode/show?

**Score schema**:
```json
{
  "comedy_pacing": {"score": 7, "reasoning": "Good rhythm but two punchlines land back-to-back without a beat"},
  "ensemble_dynamics": {"score": 9, "reasoning": "Rachel and Joey dynamic feels authentic"},
  "narrative_arc": {"score": 6, "reasoning": "Scene opens well but resolution is abrupt"},
  "thematic_coherence": {"score": 8, "reasoning": "Tone consistent with Friends apartment comedy"},
  "overall_score": 7.4,
  "summary": "A solid scene with strong character dynamic; pacing needs a breath before the final punchline."
}
```

## Character Voice Profiles (Phrase Judge Prompt)

Baked into the phrase judge system prompt — not loaded at runtime:

| Character | Core signals | Red flags |
|-----------|-------------|-----------|
| RACHEL | Fashion/beauty references, emotional candour, past-privilege irony | Academic or scientific vocabulary |
| MONICA | Competition framing, cooking/food metaphors, direct instruction | Careless or disorganised language |
| PHOEBE | Non-sequiturs, spiritual/mystical references, earnest tone | Cynicism, sarcasm without warmth |
| JOEY | Short sentences, food/acting references, literal interpretation | Sarcasm, complex abstractions |
| CHANDLER | Rhetorical self-deprecation, parenthetical jokes, "Could X BE…" | Earnest declarations without undercut |
| ROSS | Scientific analogies, over-explanation, passionate digression | Casual dismissal of facts |

Unknown characters: score `character_authenticity` as null; report "unknown character — authenticity not scored."

## CLI

**Decision**: `holodeck dialogue-eval` Typer sub-app registered in `main.py`. Two commands:
- `holodeck dialogue-eval run <path-to-dialogue-json>` — evaluate a single dialogue metadata file
- `holodeck dialogue-eval batch` — evaluate all golden fixture entries, print summary table

Input JSON format matches `dialogue_audio_metadata` structure: `[{character, text, file}]`.
