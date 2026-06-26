from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from holodeck.agents.dialogue_eval.schemas import SceneScore

VALID_SCENE_RESPONSE = json.dumps({
    "comedy_pacing": {"score": 8, "reasoning": "Good rhythm with clear setup/punchline"},
    "ensemble_dynamics": {"score": 9, "reasoning": "Rachel/Joey dynamic feels authentic"},
    "narrative_arc": {"score": 6, "reasoning": "Scene opens well but resolution is abrupt"},
    "thematic_coherence": {"score": 8, "reasoning": "Consistent Friends apartment tone"},
    "summary": "A solid scene with authentic character dynamics; the narrative arc needs a resolution beat.",
})


def _make_agent_response(content: str) -> MagicMock:
    run_response = MagicMock()
    run_response.content = content
    return run_response


_SIX_LINES: list[tuple[str, str]] = [
    ("RACHEL", "Ugh, this machine is disgusting."),
    ("JOEY", "I'm working."),
    ("RACHEL", "You're looking at a sandwich."),
    ("JOEY", "It's research."),
    ("RACHEL", "There is mould in here."),
    ("JOEY", "Yeah, I named them."),
]


class TestSceneJudgeValidResponse:
    def test_valid_transcript_returns_scene_score(self) -> None:
        from holodeck.agents.dialogue_eval.scene_judge import SceneJudge

        judge = SceneJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(VALID_SCENE_RESPONSE)):
            result = judge.score(_SIX_LINES)

        assert isinstance(result, SceneScore)
        assert result.comedy_pacing.score == 8
        assert result.ensemble_dynamics.score == 9
        assert result.line_count == 6

    def test_overall_score_computed_not_from_llm(self) -> None:
        from holodeck.agents.dialogue_eval.scene_judge import SceneJudge

        judge = SceneJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(VALID_SCENE_RESPONSE)):
            result = judge.score(_SIX_LINES)

        expected = 8 * 0.30 + 9 * 0.30 + 6 * 0.25 + 8 * 0.15
        assert result.overall_score == pytest.approx(expected)

    def test_summary_preserved_from_llm(self) -> None:
        from holodeck.agents.dialogue_eval.scene_judge import SceneJudge

        judge = SceneJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response(VALID_SCENE_RESPONSE)):
            result = judge.score(_SIX_LINES)

        assert "authentic character dynamics" in result.summary


class TestSceneJudgeInsufficientDialogue:
    def test_single_line_returns_fallback_without_llm_call(self) -> None:
        from holodeck.agents.dialogue_eval.scene_judge import SceneJudge

        judge = SceneJudge()
        agent = judge._get_agent()
        with patch.object(agent, "run") as mock_run:
            result = judge.score([("RACHEL", "Hey!")])
            mock_run.assert_not_called()

        assert isinstance(result, SceneScore)
        assert result.line_count == 1
        assert "insufficient" in result.summary.lower()

    def test_empty_list_returns_fallback_without_llm_call(self) -> None:
        from holodeck.agents.dialogue_eval.scene_judge import SceneJudge

        judge = SceneJudge()
        agent = judge._get_agent()
        with patch.object(agent, "run") as mock_run:
            result = judge.score([])
            mock_run.assert_not_called()

        assert result.line_count == 0


class TestSceneJudgeErrorHandling:
    def test_malformed_json_raises_value_error(self) -> None:
        from holodeck.agents.dialogue_eval.scene_judge import SceneJudge

        judge = SceneJudge()
        with patch.object(judge._get_agent(), "run", return_value=_make_agent_response("not json")):
            with pytest.raises(ValueError, match="Failed to parse"):
                judge.score(_SIX_LINES)
