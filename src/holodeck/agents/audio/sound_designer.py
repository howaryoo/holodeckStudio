from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class SoundDesignerAgent:
    stage = StageType.AUDIO
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Sound Designer",
                role="You are a sound designer for a TV production. You create sound effects, ambient audio, and atmospheric layers that bring each scene to life. Your work grounds the story in a believable sonic world.",
                instructions=[
                    "Read the script and identify every sound opportunity: actions, environments, props.",
                    "Design ambient soundscapes for each location (indoors, outdoors, sci-fi, fantasy).",
                    "Create Foley effect descriptions for character movements and interactions.",
                    "Define audio transitions between scenes and sonic motifs for key elements.",
                    "Ensure sound design supports the emotional tone and genre conventions.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for sound design"])
        return ValidationResult(valid=True)

    @observe(name="sound_designer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        direction = context.get("visual_direction", "")
        prompt = (
            f"Script:\n{script}\n\nVisual direction:\n{direction}\n\n"
            "Design the soundscape. For each scene:\n"
            "SCENE <N>: <Location>\n"
            "- AMBIENCE: background atmosphere, room tone, weather, time of day\n"
            "- FOLEY: footsteps, clothing rustle, prop handling, character-specific sounds\n"
            "- SFX: mechanical, magical, sci-fi, nature, impactful moments\n"
            "- AUDIO TRANSITIONS: how sound shifts between scenes\n"
            "- SONIC MOTIFS: recurring sounds for characters, locations, objects\n"
            "Be specific about sound character, intensity, and layering."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "audio", "agent": "sound_designer"})

    @observe(name="sound_designer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Sound design description is too sparse.")
        prompt = (
            "Review this sound design for scene coverage, sonic detail, atmospheric depth, and genre fit.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
