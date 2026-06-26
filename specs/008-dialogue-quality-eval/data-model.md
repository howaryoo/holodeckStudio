# Data Model: Dialogue Quality Evaluation

**Branch**: `008-dialogue-quality-eval` | **Date**: 2026-06-26

## Pydantic Models (`agents/dialogue_eval/schemas.py`)

### `DimensionResult`

```python
class DimensionResult(BaseModel):
    score: int = Field(ge=0, le=10)
    reasoning: str
```

One dimension score with its reasoning. Used for both per-phrase dimensions and scene-level dimensions.

---

### `LinePhraseScore`

```python
class LinePhraseScore(BaseModel):
    character: str                           # uppercase character name, e.g. "RACHEL"
    text: str                                # the spoken dialogue line (verbatim)
    character_authenticity: DimensionResult  # weight 0.4
    dialogue_naturalness: DimensionResult    # weight 0.35
    comedy_contribution: DimensionResult     # weight 0.25
    composite_score: float                   # computed: weighted average of 3 dimensions (0–10)
```

**Validation**: `composite_score` is a computed property, not stored from LLM output — prevents hallucinated composites.

---

### `SceneScore`

```python
class SceneScore(BaseModel):
    comedy_pacing: DimensionResult       # weight 0.30
    ensemble_dynamics: DimensionResult   # weight 0.30
    narrative_arc: DimensionResult       # weight 0.25
    thematic_coherence: DimensionResult  # weight 0.15
    overall_score: float                 # computed weighted average (0–10)
    summary: str                         # 1–2 sentence holistic description
    line_count: int                      # number of dialogue lines evaluated
    evaluated_at: datetime
```

---

### `GoldenConversationEntry`

```python
class GoldenConversationEntry(BaseModel):
    prompt_id: str                        # unique slug, e.g. "friends-kitchen-001"
    user_prompt: str                      # the holodeck produce prompt
    description: str                      # human-readable description of the scene
    expected_characters: list[str]        # e.g. ["RACHEL", "JOEY"]
    quality_notes: str                    # what "good" looks like for this scene
```

Loaded from JSON fixture files in `tests/fixtures/dialogue/` at runtime. Not persisted to DB.

---

## Fixture File Format (`tests/fixtures/dialogue/friends_kitchen_argument.json`)

```json
{
  "prompt_id": "friends-kitchen-001",
  "user_prompt": "Rachel and Joey are talking about their Thursday night — Joey is working on a scene on his PC while Rachel cleans the washing machine",
  "description": "Casual apartment scene: Joey distracted by acting prep, Rachel domestic frustration, low-stakes comedy",
  "expected_characters": ["RACHEL", "JOEY"],
  "quality_notes": "Joey should be literal and food-focused. Rachel should escalate frustration comedically. Scene needs a small resolution beat.",
  "dialogue": [
    {"character": "RACHEL", "text": "Ugh, this machine is disgusting. Joey, how do you live like this?", "file": ""},
    {"character": "JOEY", "text": "I don't live like anything, I'm working.", "file": ""}
  ]
}
```

The `"dialogue"` key holds the `dialogue_audio_metadata` list used as evaluation input. `"file"` is always ignored by the evaluator.

---

## Data Flow

```
GoldenConversationEntry (JSON fixture)
  └─ dialogue list [{character, text, file}, ...]
       │
       ▼ (file field ignored)
  PhraseJudge × N lines → list[LinePhraseScore]
       │
  SceneJudge × 1 call  → SceneScore
       │
       ▼
  CLI prints results (no persistence)
```
