from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from agno.agent import Agent

from holodeck.agents.dialogue_eval.schemas import DimensionResult, SceneScore
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model

_SYSTEM_PROMPT = """You are a holistic scene quality judge for the TV show Friends.
You evaluate a full dialogue transcript and score the scene across four dimensions.

## Scoring Dimensions

### comedy_pacing (weight 0.30)
Are jokes well-timed? Is there a rhythm of setup → punchline across the scene?
10 = perfect comedic timing throughout; 0 = no discernible comedic rhythm

### ensemble_dynamics (weight 0.30)
Does the conversation reflect real character relationships and interactions?
10 = characters feel completely authentic to each other; 0 = characters could be anybody

### narrative_arc (weight 0.25)
Does the scene have a beginning, middle, and end — a small story?
10 = clear arc with a satisfying resolution; 0 = scene just stops with no arc

### thematic_coherence (weight 0.15)
Does the scene feel like it belongs to the same episode and show?
10 = completely consistent with Friends tone and themes; 0 = tonally wrong

## Output Format
Return ONLY a JSON object with these exact keys:
{
  "comedy_pacing": {"score": <int 0-10>, "reasoning": "<1-2 sentences>"},
  "ensemble_dynamics": {"score": <int 0-10>, "reasoning": "<1-2 sentences>"},
  "narrative_arc": {"score": <int 0-10>, "reasoning": "<1-2 sentences>"},
  "thematic_coherence": {"score": <int 0-10>, "reasoning": "<1-2 sentences>"},
  "summary": "<1-2 sentence holistic description of the scene's quality>"
}

No markdown, no preamble. JSON only.
"""

_FALLBACK_DIMENSION = DimensionResult(score=5, reasoning="Insufficient dialogue for scoring")


def _extract_json(content: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError(f"Failed to parse SceneJudge response — no JSON found: {content[:200]!r}")
    try:
        return json.loads(match.group())  # type: ignore[no-any-return]
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse SceneJudge response — invalid JSON: {exc}") from exc


class SceneJudge:
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict[str, Any] = dict(
                name="SceneJudge",
                role="Evaluate full dialogue scenes for comedy, dynamics, arc, and coherence.",
                instructions=[_SYSTEM_PROMPT],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    @observe(name="scene_judge.score", as_type="generation")
    def score(self, lines: list[tuple[str, str]]) -> SceneScore:
        if len(lines) < 2:
            return SceneScore(
                comedy_pacing=_FALLBACK_DIMENSION,
                ensemble_dynamics=_FALLBACK_DIMENSION,
                narrative_arc=_FALLBACK_DIMENSION,
                thematic_coherence=_FALLBACK_DIMENSION,
                summary="Insufficient dialogue for ensemble scoring.",
                line_count=len(lines),
            )

        transcript = "\n".join(f"{char}: {text}" for char, text in lines)
        prompt = f"## Dialogue Transcript\n\n{transcript}"
        response = self._get_agent().run(prompt)
        raw = _extract_json(str(response.content))

        return SceneScore(
            comedy_pacing=DimensionResult(**raw["comedy_pacing"]),
            ensemble_dynamics=DimensionResult(**raw["ensemble_dynamics"]),
            narrative_arc=DimensionResult(**raw["narrative_arc"]),
            thematic_coherence=DimensionResult(**raw["thematic_coherence"]),
            summary=raw["summary"],
            line_count=len(lines),
        )
