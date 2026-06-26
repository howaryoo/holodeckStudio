from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from holodeck.agents.dialogue_eval.schemas import (
    GoldenConversationEntry,
    LinePhraseScore,
    SceneScore,
)

if TYPE_CHECKING:
    from agno.models.base import Model

logger = logging.getLogger(__name__)

_MAX_LINES = 50


class DialogueEvaluationRunner:
    def __init__(self, model: Model | None = None) -> None:
        self._model = model
        self._phrase_judge: Any = None
        self._scene_judge: Any = None

    def _get_phrase_judge(self) -> Any:  # noqa: ANN401
        if self._phrase_judge is None:
            from holodeck.agents.dialogue_eval.phrase_judge import PhraseJudge
            self._phrase_judge = PhraseJudge(model=self._model)
        return self._phrase_judge

    def _get_scene_judge(self) -> Any:  # noqa: ANN401
        if self._scene_judge is None:
            from holodeck.agents.dialogue_eval.scene_judge import SceneJudge
            self._scene_judge = SceneJudge(model=self._model)
        return self._scene_judge

    def evaluate(
        self, dialogue: list[dict[str, str]]
    ) -> tuple[list[LinePhraseScore], SceneScore]:
        if len(dialogue) > _MAX_LINES:
            logger.warning(
                "Dialogue has %d lines; truncating to first %d for evaluation",
                len(dialogue),
                _MAX_LINES,
            )
            dialogue = dialogue[:_MAX_LINES]

        phrase_judge = self._get_phrase_judge()
        scene_judge = self._get_scene_judge()

        line_scores: list[LinePhraseScore] = []
        for entry in dialogue:
            character = entry.get("character", "")
            text = entry.get("text", "")
            line_scores.append(phrase_judge.score(character, text))

        lines_for_scene = [
            (entry.get("character", ""), entry.get("text", "")) for entry in dialogue
        ]
        scene_score = scene_judge.score(lines_for_scene)

        return line_scores, scene_score

    def evaluate_fixture(self, fixture_path: str) -> tuple[list[LinePhraseScore], SceneScore]:
        raw = json.loads(Path(fixture_path).read_text())
        entry = GoldenConversationEntry.model_validate(raw)
        return self.evaluate(entry.dialogue)
