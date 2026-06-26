from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from holodeck.agents.dialogue_eval.schemas import DimensionResult, LinePhraseScore


VALID_LLM_RESPONSE = json.dumps({
    "character_authenticity": {"score": 8, "reasoning": "Rachel's sarcasm is spot-on"},
    "dialogue_naturalness": {"score": 9, "reasoning": "Easy to deliver"},
    "comedy_contribution": {"score": 7, "reasoning": "Good setup for the scene"},
})

UNKNOWN_CHAR_RESPONSE = json.dumps({
    "dialogue_naturalness": {"score": 7, "reasoning": "Natural line"},
    "comedy_contribution": {"score": 6, "reasoning": "Mild comedy"},
})


def _make_agent_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    run_response = MagicMock()
    run_response.content = content
    return run_response


class TestPhraseJudgeValidResponse:
    def test_known_character_returns_line_phrase_score(self) -> None:
        from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge

        judge = PhraseJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(VALID_LLM_RESPONSE)):
            result = judge.score("RACHEL", "Ugh, this machine is disgusting.")

        assert isinstance(result, LinePhraseScore)
        assert result.character == "RACHEL"
        assert result.character_authenticity.score == 8
        assert result.dialogue_naturalness.score == 9
        assert result.comedy_contribution.score == 7

    def test_composite_score_computed_not_from_llm(self) -> None:
        from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge

        judge = PhraseJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(VALID_LLM_RESPONSE)):
            result = judge.score("RACHEL", "Ugh, this machine is disgusting.")

        expected = 8 * 0.40 + 9 * 0.35 + 7 * 0.25
        assert result.composite_score == pytest.approx(expected)


class TestPhraseJudgeUnknownCharacter:
    def test_unknown_character_gets_zero_authenticity(self) -> None:
        from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge

        judge = PhraseJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(UNKNOWN_CHAR_RESPONSE)):
            result = judge.score("GUNTHER", "I love Rachel.")

        assert result.character_authenticity.score == 0
        assert "unknown character" in result.character_authenticity.reasoning.lower()

    def test_unknown_character_still_scores_other_dimensions(self) -> None:
        from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge

        judge = PhraseJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(UNKNOWN_CHAR_RESPONSE)):
            result = judge.score("GUNTHER", "I love Rachel.")

        assert result.dialogue_naturalness.score == 7
        assert result.comedy_contribution.score == 6


class TestPhraseJudgeErrorHandling:
    def test_malformed_json_raises_value_error(self) -> None:
        from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge

        judge = PhraseJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response("not json at all")):
            with pytest.raises(ValueError, match="Failed to parse"):
                judge.score("RACHEL", "Some text")

    def test_empty_text_returns_zero_scores(self) -> None:
        from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge

        judge = PhraseJudge()
        result = judge.score("RACHEL", "")

        assert isinstance(result, LinePhraseScore)
        assert result.comedy_contribution.score == 0
        assert result.character_authenticity.score == 0
        assert result.dialogue_naturalness.score == 0
        assert "empty" in result.comedy_contribution.reasoning.lower()
