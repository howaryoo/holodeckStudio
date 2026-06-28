from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class ComposerAgent:
    stage = StageType.AUDIO
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Composer",
                role="You are a composer for a TV production. You create musical themes, background scores, and soundscapes that match the emotional arc and pacing of each scene. Your music enhances narrative tension, character moments, and world-building.",
                instructions=[
                    "Analyze the script and creative direction for emotional beats and pacing.",
                    "Compose musical themes for main characters, locations, and key story arcs.",
                    "Define instrumentation, tempo, key, and mood for each scene's score.",
                    "Match musical style to the production's genre and visual tone.",
                    "Provide detailed descriptions of how music evolves across the episode.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for musical composition"])
        return ValidationResult(valid=True)

    @observe(name="composer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        theme = context.get("creative_direction", "")
        style_guide = context.get("visual_style", "")
        prompt = (
            f"Script:\n{script}\n\nCreative direction: {theme}\n\n"
            f"Visual style guide:\n{style_guide}\n\n"
            "Compose the musical score. For each scene:\n"
            "SCENE <N>: <Location>\n"
            "- THEME: primary musical motif and emotional intent\n"
            "- INSTRUMENTATION: instruments and ensemble\n"
            "- TEMPO: bpm range and rhythm pattern\n"
            "- KEY/MODE: musical key and scale\n"
            "- DYNAMICS: volume and intensity arc\n"
            "- TRANSITION: how score shifts to next scene\n"
            "Include a main title theme description and end credits approach."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "audio", "agent": "composer"})

    @observe(name="composer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Musical score description is too sparse.")
        prompt = (
            "Review this musical composition for emotional alignment, thematic coherence, and scene-specific detail.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
