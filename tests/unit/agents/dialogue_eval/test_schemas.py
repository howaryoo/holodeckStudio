from __future__ import annotations

import pytest
from pydantic import ValidationError

from holodeck.agents.dialogue_eval.schemas import (
    DimensionResult,
    GoldenConversationEntry,
    LinePhraseScore,
    SceneScore,
    _PHRASE_WEIGHTS,
    _SCENE_WEIGHTS,
)


def _phrase_score(**overrides: int) -> LinePhraseScore:
    defaults = {"character_authenticity": 8, "dialogue_naturalness": 7, "comedy_contribution": 6}
    defaults.update(overrides)
    return LinePhraseScore(
        character="RACHEL",
        text="Hey Joey!",
        character_authenticity=DimensionResult(score=defaults["character_authenticity"], reasoning="good"),
        dialogue_naturalness=DimensionResult(score=defaults["dialogue_naturalness"], reasoning="good"),
        comedy_contribution=DimensionResult(score=defaults["comedy_contribution"], reasoning="good"),
    )


def _scene_score(**overrides: int) -> SceneScore:
    defaults = {
        "comedy_pacing": 8,
        "ensemble_dynamics": 7,
        "narrative_arc": 6,
        "thematic_coherence": 9,
    }
    defaults.update(overrides)
    return SceneScore(
        comedy_pacing=DimensionResult(score=defaults["comedy_pacing"], reasoning="r"),
        ensemble_dynamics=DimensionResult(score=defaults["ensemble_dynamics"], reasoning="r"),
        narrative_arc=DimensionResult(score=defaults["narrative_arc"], reasoning="r"),
        thematic_coherence=DimensionResult(score=defaults["thematic_coherence"], reasoning="r"),
        summary="Test summary.",
        line_count=6,
    )


class TestPhraseWeights:
    def test_weights_sum_to_one(self) -> None:
        assert abs(sum(_PHRASE_WEIGHTS.values()) - 1.0) < 1e-9

    def test_composite_score_computed_correctly(self) -> None:
        ps = _phrase_score(character_authenticity=10, dialogue_naturalness=10, comedy_contribution=10)
        assert ps.composite_score == pytest.approx(10.0)

    def test_composite_score_weighted(self) -> None:
        ps = _phrase_score(character_authenticity=10, dialogue_naturalness=0, comedy_contribution=0)
        assert ps.composite_score == pytest.approx(10 * 0.40)


class TestSceneWeights:
    def test_weights_sum_to_one(self) -> None:
        assert abs(sum(_SCENE_WEIGHTS.values()) - 1.0) < 1e-9

    def test_overall_score_computed_correctly(self) -> None:
        ss = _scene_score(
            comedy_pacing=10, ensemble_dynamics=10, narrative_arc=10, thematic_coherence=10
        )
        assert ss.overall_score == pytest.approx(10.0)

    def test_overall_score_weighted(self) -> None:
        ss = _scene_score(
            comedy_pacing=10, ensemble_dynamics=0, narrative_arc=0, thematic_coherence=0
        )
        assert ss.overall_score == pytest.approx(10 * 0.30)


class TestDimensionResult:
    def test_score_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionResult(score=-1, reasoning="bad")

    def test_score_above_ten_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionResult(score=11, reasoning="bad")

    def test_score_zero_accepted(self) -> None:
        d = DimensionResult(score=0, reasoning="zero")
        assert d.score == 0

    def test_score_ten_accepted(self) -> None:
        d = DimensionResult(score=10, reasoning="perfect")
        assert d.score == 10


class TestGoldenConversationEntry:
    def test_valid_entry(self) -> None:
        entry = GoldenConversationEntry(
            prompt_id="test-001",
            user_prompt="Rachel and Joey argue",
            description="Kitchen argument",
            expected_characters=["RACHEL", "JOEY"],
            quality_notes="Should be comedic",
            dialogue=[{"character": "RACHEL", "text": "Ugh!", "file": ""}],
        )
        assert entry.prompt_id == "test-001"
        assert len(entry.dialogue) == 1
