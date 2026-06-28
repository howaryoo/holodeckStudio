from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from holodeck.agents.dialogue_eval.schemas import DimensionResult, LinePhraseScore, SceneScore


def _make_line_score(character: str = "RACHEL", text: str = "Hi") -> LinePhraseScore:
    dim = DimensionResult(score=7, reasoning="ok")
    return LinePhraseScore(
        character=character, text=text,
        character_authenticity=dim,
        dialogue_naturalness=dim,
        comedy_contribution=dim,
    )


def _make_scene_score(n: int = 2) -> SceneScore:
    dim = DimensionResult(score=7, reasoning="ok")
    return SceneScore(
        comedy_pacing=dim, ensemble_dynamics=dim,
        narrative_arc=dim, thematic_coherence=dim,
        summary="Good scene.", line_count=n,
    )


_DIALOGUE_2 = [
    {"character": "RACHEL", "text": "Hello!", "file": "some/path.mp3"},
    {"character": "JOEY", "text": "Hey!", "file": "other/path.mp3"},
]

_DIALOGUE_3 = _DIALOGUE_2 + [{"character": "MONICA", "text": "Hi!", "file": ""}]


class TestDialogueRunnerEvaluate:
    def test_calls_phrase_judge_once_per_line(self) -> None:
        from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

        runner = DialogueEvaluationRunner()
        mock_phrase = MagicMock()
        mock_phrase.score.return_value = _make_line_score()
        mock_scene = MagicMock()
        mock_scene.score.return_value = _make_scene_score(2)

        runner._phrase_judge = mock_phrase
        runner._scene_judge = mock_scene

        runner.evaluate(_DIALOGUE_2)

        assert mock_phrase.score.call_count == 2

    def test_calls_scene_judge_exactly_once(self) -> None:
        from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

        runner = DialogueEvaluationRunner()
        mock_phrase = MagicMock()
        mock_phrase.score.return_value = _make_line_score()
        mock_scene = MagicMock()
        mock_scene.score.return_value = _make_scene_score(3)

        runner._phrase_judge = mock_phrase
        runner._scene_judge = mock_scene

        runner.evaluate(_DIALOGUE_3)

        mock_scene.score.assert_called_once()

    def test_file_field_is_ignored(self) -> None:
        from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

        runner = DialogueEvaluationRunner()
        mock_phrase = MagicMock()
        mock_phrase.score.return_value = _make_line_score()
        mock_scene = MagicMock()
        mock_scene.score.return_value = _make_scene_score(2)

        runner._phrase_judge = mock_phrase
        runner._scene_judge = mock_scene

        runner.evaluate(_DIALOGUE_2)

        calls = mock_phrase.score.call_args_list
        for call in calls:
            args = call.args
            assert len(args) == 2
            assert "file" not in str(args)

    def test_returns_tuple_of_line_scores_and_scene_score(self) -> None:
        from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

        runner = DialogueEvaluationRunner()
        mock_phrase = MagicMock()
        mock_phrase.score.return_value = _make_line_score()
        mock_scene = MagicMock()
        mock_scene.score.return_value = _make_scene_score(2)

        runner._phrase_judge = mock_phrase
        runner._scene_judge = mock_scene

        line_scores, scene_score = runner.evaluate(_DIALOGUE_2)

        assert len(line_scores) == 2
        assert isinstance(scene_score, SceneScore)


class TestDialogueRunnerTruncation:
    def test_truncates_to_50_lines_and_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

        runner = DialogueEvaluationRunner()
        mock_phrase = MagicMock()
        mock_phrase.score.return_value = _make_line_score()
        mock_scene = MagicMock()
        mock_scene.score.return_value = _make_scene_score(50)

        runner._phrase_judge = mock_phrase
        runner._scene_judge = mock_scene

        long_dialogue = [{"character": "RACHEL", "text": f"Line {i}", "file": ""} for i in range(60)]

        with caplog.at_level(logging.WARNING, logger="holodeck.evaluation.dialogue_runner"):
            runner.evaluate(long_dialogue)

        assert mock_phrase.score.call_count == 50
        assert any("truncating" in rec.message.lower() for rec in caplog.records)


class TestDialogueRunnerFixture:
    def test_evaluate_fixture_loads_and_evaluates(self, tmp_path) -> None:
        from holodeck.evaluation.dialogue_runner import DialogueEvaluationRunner

        fixture = {
            "prompt_id": "test-001",
            "user_prompt": "Rachel and Joey talk",
            "description": "test",
            "expected_characters": ["RACHEL", "JOEY"],
            "quality_notes": "be good",
            "dialogue": [
                {"character": "RACHEL", "text": "Hey!", "file": ""},
                {"character": "JOEY", "text": "Hi!", "file": ""},
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        runner = DialogueEvaluationRunner()
        mock_phrase = MagicMock()
        mock_phrase.score.return_value = _make_line_score()
        mock_scene = MagicMock()
        mock_scene.score.return_value = _make_scene_score(2)
        runner._phrase_judge = mock_phrase
        runner._scene_judge = mock_scene

        line_scores, scene_score = runner.evaluate_fixture(str(fixture_path))

        assert len(line_scores) == 2
        assert isinstance(scene_score, SceneScore)
