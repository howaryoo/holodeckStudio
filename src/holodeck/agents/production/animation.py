from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class AnimationAgent:
    stage = StageType.ANIMATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Animator",
                role="You are a scene animator. You take storyboard descriptions, character art, and background art and create detailed scene animation descriptions: motion paths, timing, character blocking, camera movement, and visual effects.",
                instructions=[
                    "Translate storyboard frames into animated motion descriptions.",
                    "Define character blocking and movement paths within each scene.",
                    "Plan camera movements: pans, zooms, dolly shots, cuts.",
                    "Specify timing and pacing: scene duration, keyframe intervals.",
                    "Describe visual effects: particle systems, lighting changes, transitions.",
                    "Ensure animation maintains visual consistency with the style guide.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("storyboard"):
            return ValidationResult(valid=False, errors=["Storyboard required for animation"])
        return ValidationResult(valid=True)

    @observe(name="animation.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        storyboard = context.get("storyboard", "")
        visual_direction = context.get("visual_direction", "")
        assets = context.get("asset_descriptions", "")
        script = context.get("script", "")
        prompt = (
            f"Script:\n{script}\n\nStoryboard:\n{storyboard}\n\nVisual direction:\n{visual_direction}\n\n"
            f"Asset descriptions:\n{assets}\n\n"
            "Create scene animation descriptions. For each scene:\n"
            "SCENE <N>: <Location>\n"
            "- DURATION: seconds\n"
            "- BLOCKING: character positions, movements, interactions\n"
            "- CAMERA: type (static/pan/track/dolly/zoom), start position, end position\n"
            "- KEYFRAMES: frame-by-frame breakdown of major actions\n"
            "- VFX: particle effects, lighting shifts, weather, transitions\n"
            "- TIMING: pacing curve (slow/fast build), beat markers\n"
            "Be precise about motion, timing, and spatial relationships."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "animation", "agent": "animation"})

    @observe(name="animation.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Animation description is too sparse.")
        prompt = (
            "Review these scene animation descriptions for motion clarity, timing specificity, camera work, and visual effect coverage.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
