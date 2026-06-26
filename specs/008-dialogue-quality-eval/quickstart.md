# Quickstart: Dialogue Quality Evaluation

## Prerequisites

- Holodeck infra running: `make start`
- `.env` configured with a valid LLM provider (used for LLM-as-judge calls)

## Evaluate a Single Dialogue

### Step 1 — Run a production to get dialogue output

```bash
uv run holodeck produce "Rachel and Joey are arguing about Thursday night plans" \
  --bible <bible-id>
# Note the dialogue_audio_metadata output from === DIALOGUE AUDIO ===
```

### Step 2 — Save dialogue lines to a JSON file

```json
[
  {"character": "RACHEL", "text": "Ugh, this machine is disgusting. Joey, how do you live like this?", "file": ""},
  {"character": "JOEY", "text": "I don't live like anything, I'm working.", "file": ""}
]
```

```bash
# Save as dialogue.json
```

### Step 3 — Run evaluation

```bash
uv run holodeck dialogue-eval run dialogue.json --prompt-id friends-kitchen-001
```

Expected output:
```
=== DIALOGUE EVALUATION ===

Per-phrase scores:
  [RACHEL] Ugh, this machine is disgusting...
    Character authenticity : 9/10  Rachel's frustration escalation is spot-on
    Dialogue naturalness   : 8/10  Natural line, easy to deliver
    Comedy contribution    : 7/10  Sets up the contrast nicely
    Composite              : 8.2/10

  [JOEY] I don't live like anything, I'm working.
    Character authenticity : 8/10  Joey's distracted literalism
    Dialogue naturalness   : 9/10  Very naturalistic
    Comedy contribution    : 8/10  Good deadpan punchline
    Composite              : 8.4/10

Scene score: 8.1/10
  Comedy pacing       : 8/10  Good setup → punchline rhythm
  Ensemble dynamics   : 9/10  Rachel/Joey dynamic feels authentic
  Narrative arc       : 6/10  Scene ends abruptly, no resolution beat
  Thematic coherence  : 8/10  Consistent Friends apartment tone

  "A strong scene opener with authentic Rachel/Joey chemistry. The narrative arc needs a small resolution beat to feel complete."
```

## Batch Evaluate Golden Dataset

```bash
uv run holodeck dialogue-eval batch
```

Expected output: summary table of all golden entries with their scores and regression flags.

## Unit Tests

```bash
uv run pytest tests/unit/agents/dialogue_eval/ tests/unit/evaluation/test_dialogue_runner.py -v
```

These tests use fixture files from `tests/fixtures/dialogue/` — no LLM or DB required.
