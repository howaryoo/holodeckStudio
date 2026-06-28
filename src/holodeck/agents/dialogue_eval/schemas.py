from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

_PHRASE_WEIGHTS = {
    "character_authenticity": 0.40,
    "dialogue_naturalness": 0.35,
    "comedy_contribution": 0.25,
}

_SCENE_WEIGHTS = {
    "comedy_pacing": 0.30,
    "ensemble_dynamics": 0.30,
    "narrative_arc": 0.25,
    "thematic_coherence": 0.15,
}


class DimensionResult(BaseModel):
    score: int = Field(ge=0, le=10)
    reasoning: str


class LinePhraseScore(BaseModel):
    character: str
    text: str
    character_authenticity: DimensionResult
    dialogue_naturalness: DimensionResult
    comedy_contribution: DimensionResult

    @property
    def composite_score(self) -> float:
        return (
            self.character_authenticity.score * _PHRASE_WEIGHTS["character_authenticity"]
            + self.dialogue_naturalness.score * _PHRASE_WEIGHTS["dialogue_naturalness"]
            + self.comedy_contribution.score * _PHRASE_WEIGHTS["comedy_contribution"]
        )

    @model_validator(mode="after")
    def _weights_sum(self) -> LinePhraseScore:
        total = sum(_PHRASE_WEIGHTS.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Phrase dimension weights must sum to 1.0, got {total}")
        return self


class SceneScore(BaseModel):
    comedy_pacing: DimensionResult
    ensemble_dynamics: DimensionResult
    narrative_arc: DimensionResult
    thematic_coherence: DimensionResult
    summary: str
    line_count: int

    @property
    def overall_score(self) -> float:
        return (
            self.comedy_pacing.score * _SCENE_WEIGHTS["comedy_pacing"]
            + self.ensemble_dynamics.score * _SCENE_WEIGHTS["ensemble_dynamics"]
            + self.narrative_arc.score * _SCENE_WEIGHTS["narrative_arc"]
            + self.thematic_coherence.score * _SCENE_WEIGHTS["thematic_coherence"]
        )

    @model_validator(mode="after")
    def _weights_sum(self) -> SceneScore:
        total = sum(_SCENE_WEIGHTS.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Scene dimension weights must sum to 1.0, got {total}")
        return self


class GoldenConversationEntry(BaseModel):
    prompt_id: str
    user_prompt: str
    description: str
    expected_characters: list[str]
    quality_notes: str
    dialogue: list[dict[str, str]]
