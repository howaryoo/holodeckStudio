from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class QualityGuidelines(BaseModel):
    narrative_goal: str
    character_arcs: dict[str, str]
    comedy_approach: str
    emotional_beats: list[str]
    production_constraints: list[str]
    thematic_focus: str


class ScopeBoundaries(BaseModel):
    must_include: list[str]
    must_exclude: list[str]
    character_focus: list[str]


class GoldenDatasetEntry(BaseModel):
    prompt_id: str
    user_prompt: str
    quality_guidelines: QualityGuidelines
    scope_boundaries: ScopeBoundaries
    acceptable_variations: list[str]
    created_by: str = "content-team"
    version: str = "1.0"


class DimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


class GuidelineComparison(BaseModel):
    met: list[str] = Field(default_factory=list)
    partially_met: list[str] = Field(default_factory=list)
    missed: list[str] = Field(default_factory=list)
    variation_used: str | None = None


class EvaluationResult(BaseModel):
    result_id: UUID = Field(default_factory=uuid4)
    script_id: str
    golden_entry_id: str
    dimension_scores: list[DimensionScore]
    passed_quality_gate: bool
    red_flags_triggered: list[str] = Field(default_factory=list)
    guideline_comparison: GuidelineComparison = Field(default_factory=GuidelineComparison)
    evaluation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    previous_score: float | None = None
    regression_detected: bool = False

    def overall_score(self) -> float:
        return sum(ds.weighted_score for ds in self.dimension_scores)


class EvaluationFailure(BaseModel):
    golden_entry_id: str
    error_message: str
    error_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SummaryStatistics(BaseModel):
    total_entries: int
    evaluated: int
    failed: int
    pass_count: int
    fail_count: int
    average_overall_score: float
    average_score_by_dimension: dict[str, float]
    regressions_detected: int
    common_red_flags: list[str]


class BatchEvaluationReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    golden_dataset_version: str
    evaluation_results: list[EvaluationResult]
    failures: list[EvaluationFailure] = Field(default_factory=list)
    summary_statistics: SummaryStatistics | None = None
    generated_timestamp: datetime = Field(default_factory=datetime.utcnow)


REJECTION_THRESHOLD: float = 0.35


class EvaluationDimension:
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
            "description": "Do characters behave in ways consistent with their established Friends personalities?",
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

    @classmethod
    def weight_sum(cls) -> float:
        return sum(d["weight"] for d in cls.DIMENSIONS.values())

    @classmethod
    def validate_weights(cls) -> None:
        total = cls.weight_sum()
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"DIMENSIONS weights must sum to 1.0, got {total}")


EvaluationDimension.validate_weights()
