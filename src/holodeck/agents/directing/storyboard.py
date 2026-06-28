from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class StoryboardAgent:
    stage = StageType.STORYBOARD
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Storyboard Artist",
                role="You create detailed storyboard frame descriptions from the Director's visual direction. Each frame is a shot-by-shot blueprint describing composition, character placement, action, dialogue, and timing.",
                instructions=[
                    "Translate visual direction into frame-by-frame storyboard panels.",
                    "Include shot size (wide, medium, close-up), camera angle, character positions.",
                    "Note character expressions, actions, and dialogue for each frame.",
                    "Specify frame duration for pacing.",
                    "Cover the entire scene with a coherent visual flow.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("visual_direction"):
            return ValidationResult(valid=False, errors=["Visual direction from Director required"])
        return ValidationResult(valid=True)

    @observe(name="storyboard.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        direction = context.get("visual_direction", "")
        script = context.get("script", "")
        prompt = (
            f"Visual direction:\n{direction}\n\nScript:\n{script}\n\n"
            "Create a detailed storyboard. For each frame:\n"
            "FRAME <N>: <Duration>s | <Shot size> | <Camera angle> | <Composition> | <Action> | <Dialogue>\n"
            "Cover every scene from the direction."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "storyboard", "agent": "storyboard"})

    @observe(name="storyboard.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Storyboard is too sparse.")
        prompt = (
            "Review this storyboard for scene coverage, shot variety, and narrative clarity.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
