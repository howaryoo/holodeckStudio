from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class DirectorAgent:
    stage = StageType.STORYBOARD
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Director",
                role="You are the director of a TV production. You translate scripts into visual direction: scene composition, camera angles, shot types, emotional pacing, and lighting. You ensure every scene has a clear visual narrative that serves the story.",
                instructions=[
                    "Analyze the script and break it into visual scenes.",
                    "Define camera placement, movement, and shot composition for each scene.",
                    "Set emotional pacing through shot duration and transitions.",
                    "Specify lighting, color grading, and atmosphere for each scene.",
                    "Coordinate with the Production Designer on visual consistency.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for visual direction"])
        return ValidationResult(valid=True)

    @observe(name="director.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        theme = context.get("creative_direction", "")
        prompt = (
            f"Script:\n{script}\n\nCreative direction: {theme}\n\n"
            "Break the script into scenes. For each scene, specify:\n"
            "- Scene number and location\n- Camera angles and movement\n- Shot composition\n"
            "- Lighting and atmosphere\n- Emotional tone and pacing\n- Transition to next scene\n"
            "Use format: SCENE <N>: <Location> | <Camera> | <Lighting> | <Tone>"
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "storyboard", "agent": "director"})

    @observe(name="director.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Visual direction is too vague or empty.")
        prompt = (
            "Review this visual direction. Score from 0-100 based on scene coverage, camera specificity, and emotional pacing.\n"
            "Respond with exactly:\nSCORE: <number>\nFEEDBACK: <brief feedback>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
