# Data Model: Golden Dataset Evaluation Framework

## Entity Overview

```
GoldenDatasetEntry ──< EvaluationResult >── DimensionScore
                                │
                         BatchEvaluationReport
                                │
                         EvaluationFailure
```

---

## GoldenDatasetEntry

Represents a single curated test case. Stored in JSON fixture files; not database-persisted.

```python
class GoldenDatasetEntry(BaseModel):
    prompt_id: str                          # Unique slug, e.g. "rival-chef-s01"
    user_prompt: str                        # Sitcom episode concept prompt
    quality_guidelines: QualityGuidelines   # Expected outcome criteria
    scope_boundaries: ScopeBoundaries       # What must/must not appear
    acceptable_variations: list[str]        # Valid alternative approaches
    created_by: str = "content-team"
    version: str = "1.0"
```

### QualityGuidelines (nested)

```python
class QualityGuidelines(BaseModel):
    narrative_goal: str             # What the episode's story should accomplish
    character_arcs: dict[str, str]  # character_name → expected arc/role
    comedy_approach: str            # Primary comedy style expected
    emotional_beats: list[str]      # Ordered list of required emotional moments
    production_constraints: list[str]  # Feasibility requirements (e.g. "2 sets max")
    thematic_focus: str             # Core theme of the episode
```

### ScopeBoundaries (nested)

```python
class ScopeBoundaries(BaseModel):
    must_include: list[str]   # Elements that MUST appear
    must_exclude: list[str]   # Elements that MUST NOT appear
    character_focus: list[str]  # Primary characters for the episode
```

---

## EvaluationDimension

Class-level constant `DIMENSIONS` (not an instance model). Injected into JudgeAgent system prompt.

```python
DIMENSIONS: ClassVar[dict[str, dict]] = {
    "narrative_coherence": {
        "description": "Does the episode tell a coherent story with a clear beginning, middle, and end?",
        "weight": 0.15,
        "signals": [
            "Plot has identifiable inciting incident",
            "A/B plots both resolve by end",
            "No unresolved subplots without intentional setup",
        ],
        "red_flags": [
            "Story ends without resolution",
            "Characters act with no motivation",
        ],
    },
    "character_consistency": {
        "description": "Do characters behave in ways consistent with their established personalities?",
        "weight": 0.20,
        "signals": [
            "Speech patterns match character bible",
            "Decisions align with character motivations",
            "Red flag behaviors from bible are absent",
        ],
        "red_flags": [
            "Joey shares food willingly",
            "Phoebe eats meat",
            "Monica's apartment is described as messy",
            "Ross lets a disagreement go without comment",
            "Chandler gives sincere emotional speech with no joke follow-up",
        ],
    },
    "comedy_effectiveness": {
        "description": "Does the episode generate genuine comedy through appropriate Friends-style humor?",
        "weight": 0.15,
        "signals": [
            "At least 3 distinct comedic beats per act",
            "Comedy arises from character traits, not situation alone",
            "Running gags land in context",
        ],
        "red_flags": [
            "No comedic beats in any 5-minute segment",
            "Humor relies on cruelty or stereotype",
        ],
    },
    "dialogue_naturalness": {
        "description": "Does dialogue feel authentic to each character's voice and the show's tone?",
        "weight": 0.15,
        "signals": [
            "Chandler's ironic emphasis present in his lines",
            "Joey uses simple vocabulary; no academic terms",
            "Ross over-explains or pivots to paleontology at least once",
            "Lines are snappy; no monologue exceeds 6 sentences",
        ],
        "red_flags": [
            "Character uses vocabulary inconsistent with their education/background",
            "Dialogue is purely expository with no comedic subtext",
        ],
    },
    "story_structure": {
        "description": "Does the episode follow Friends' A/B plot structure with appropriate act breaks?",
        "weight": 0.10,
        "signals": [
            "A-plot and B-plot clearly identifiable",
            "Cold open present",
            "Act break creates tension or comedic cliffhanger",
        ],
        "red_flags": [
            "Single linear plot with no B-story",
            "No act structure (feels like one continuous scene)",
        ],
    },
    "emotional_impact": {
        "description": "Does the episode have emotional resonance — heart beneath the humor?",
        "weight": 0.10,
        "signals": [
            "At least one scene of genuine emotional connection between characters",
            "Conflict resolves with warmth (Friends tone: never cynical)",
            "Audience would care about the outcome",
        ],
        "red_flags": [
            "Episode ends on unresolved conflict with no warmth",
            "No character expresses genuine vulnerability",
        ],
    },
    "production_feasibility": {
        "description": "Can this episode be produced within a standard Friends production context?",
        "weight": 0.10,
        "signals": [
            "All scenes set in known Friends locations or one new set",
            "No more than 6 speaking roles (core cast + 2 guests max)",
            "No scenes requiring special effects or unusual props",
        ],
        "red_flags": [
            "Episode requires more than 3 distinct sets",
            "Scenes impossible in a multi-camera studio format",
        ],
    },
    "thematic_alignment": {
        "description": "Does the episode's theme align with the expected thematic focus from the golden dataset?",
        "weight": 0.05,
        "signals": [
            "Central theme stated or implied in dialogue",
            "Character actions reinforce theme",
            "Theme consistent with Friends' core values (friendship, loyalty, growth)",
        ],
        "red_flags": [
            "Episode has no identifiable theme",
            "Theme contradicts Friends' warm, optimistic tone",
        ],
    },
}
```

**Weight sum validation**: 0.15 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 + 0.10 + 0.05 = **1.00** ✅

---

## DimensionScore

One scored dimension for a single evaluation.

```python
class DimensionScore(BaseModel):
    dimension: str          # Must match a key in DIMENSIONS
    score: float            # Constrained: 0.0 ≤ score ≤ 1.0
    weight: float           # Constrained: 0.0 ≤ weight ≤ 1.0 (copied from DIMENSIONS)
    reasoning: str = ""     # LLM-provided justification
    evidence: list[str]     # Specific quotes/excerpts from the script

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight
```

---

## EvaluationResult

Assessment outcome for one generated script against one golden dataset entry. Persisted to PostgreSQL.

```python
class EvaluationResult(BaseModel):
    result_id: UUID = Field(default_factory=uuid4)
    script_id: str                              # ID of the generated script
    golden_entry_id: str                        # prompt_id from GoldenDatasetEntry
    dimension_scores: list[DimensionScore]      # One per dimension
    overall_score: float                        # Weighted average
    passed_quality_gate: bool                   # overall_score >= REJECTION_THRESHOLD
    red_flags_triggered: list[str]              # Red flag descriptions that fired
    guideline_comparison: GuidelineComparison   # Direct mapping vs golden guidelines
    evaluation_timestamp: datetime
    previous_score: float | None = None         # overall_score from prior run (for regression)
    regression_detected: bool = False           # True if score dropped >10% vs previous

    def overall_score(self) -> float:
        return sum(ds.weighted_score for ds in self.dimension_scores)
```

### GuidelineComparison (nested)

```python
class GuidelineComparison(BaseModel):
    met: list[str]          # Guideline requirements clearly satisfied
    partially_met: list[str]  # Partially addressed
    missed: list[str]       # Requirements not addressed in the generated script
    variation_used: str | None  # Which acceptable_variation was employed
```

---

## EvaluationFailure

Captures a failed evaluation attempt within a batch run (not persisted).

```python
class EvaluationFailure(BaseModel):
    golden_entry_id: str
    error_message: str
    error_type: str         # e.g. "GenerationError", "JudgeAgentError", "ValidationError"
    timestamp: datetime
```

---

## BatchEvaluationReport

Aggregates results from a full batch run.

```python
class BatchEvaluationReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    golden_dataset_version: str             # version field from the JSON fixture
    evaluation_results: list[EvaluationResult]
    failures: list[EvaluationFailure]       # Entries that could not be evaluated
    summary_statistics: SummaryStatistics
    generated_timestamp: datetime
```

### SummaryStatistics (nested)

```python
class SummaryStatistics(BaseModel):
    total_entries: int
    evaluated: int
    failed: int
    pass_count: int                         # passed_quality_gate == True
    fail_count: int                         # passed_quality_gate == False
    average_overall_score: float
    average_score_by_dimension: dict[str, float]   # dimension → mean score
    regressions_detected: int
    common_red_flags: list[str]             # Red flags that appeared in >50% of evaluations
```

---

## State Transitions

```
GoldenDatasetEntry (static JSON)
         │
         ▼ EvaluationRunner.evaluate_single()
Script generation → JudgeAgent.process() → EvaluationResult (PENDING)
         │                                         │
         │                                         ▼
         │                               Persist to PostgreSQL
         │                               (with previous_score lookup)
         │                                         │
         ▼                                         ▼
EvaluationFailure                      EvaluationResult (COMPLETE)
(on any exception)                              │
                                                ▼
                                   BatchEvaluationReport.aggregate()
```

---

## Database Persistence

New PostgreSQL table: `evaluation_results`

| Column | Type | Notes |
|--------|------|-------|
| `result_id` | UUID PK | Generated |
| `script_id` | VARCHAR | Reference to generated script |
| `golden_entry_id` | VARCHAR | prompt_id from golden dataset |
| `overall_score` | FLOAT | Weighted average |
| `passed_quality_gate` | BOOLEAN | score >= 0.35 |
| `red_flags_triggered` | JSONB | List of triggered red flags |
| `dimension_scores` | JSONB | Full DimensionScore list serialized |
| `guideline_comparison` | JSONB | GuidelineComparison serialized |
| `previous_score` | FLOAT NULLABLE | Score from most recent prior run |
| `regression_detected` | BOOLEAN | True if dropped >10% |
| `evaluation_timestamp` | TIMESTAMPTZ | When evaluation ran |

Alembic migration required: `alembic revision --autogenerate -m "add evaluation_results table"`
