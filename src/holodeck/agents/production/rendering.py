from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class RenderingAgent:
    stage = StageType.ANIMATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Renderer",
                role="You are a rendering supervisor. You take animated scene descriptions, musical score, sound design, and voice direction and produce a final assembly plan: scene sequencing, audio-visual synchronization, output format specs, and render pipeline instructions.",
                instructions=[
                    "Assemble scenes in correct sequence with transitions.",
                    "Sync audio tracks (music, SFX, dialogue) to animation timings.",
                    "Define render output specs: resolution, frame rate, codec, color space.",
                    "Plan render pass order and compositing layers.",
                    "Describe final delivery format and quality control checks.",
                    "Ensure all elements come together into a coherent final product.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("animation"):
            return ValidationResult(valid=False, errors=["Animation descriptions required for rendering"])
        return ValidationResult(valid=True)

    @observe(name="rendering.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        animation_desc = context.get("animation", "")
        musical_score = context.get("musical_score", "")
        sound_design = context.get("sound_design", "")
        voice_direction = context.get("voice_direction", "")
        script = context.get("script", "")
        prompt = (
            f"Script:\n{script}\n\nAnimation descriptions:\n{animation_desc}\n\n"
            f"Musical score:\n{musical_score}\n\nSound design:\n{sound_design}\n\n"
            f"Voice direction:\n{voice_direction}\n\n"
            "Create the final render assembly plan:\n"
            "SCENE SEQUENCE:\n- Scene order, transitions (cut/fade/dissolve/whip pan)\n"
            "AUDIO SYNC:\n- Which audio track plays during each scene segment\n"
            "- Dialogue sync points, music cue triggers, SFX placement\n"
            "RENDER SPECS:\n- Resolution, frame rate, codec, color grading\n"
            "COMPOSITING:\n- Layer order, visual effects compositing, color correction\n"
            "DELIVERY:\n- Output format, quality check criteria\n"
            "Be specific about timing, sync points, and technical specs."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "animation", "agent": "rendering"})

    @observe(name="rendering.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Render assembly plan is too sparse.")
        prompt = (
            "Review this render assembly plan for completeness, audio-video sync accuracy, technical spec feasibility, and quality control coverage.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
