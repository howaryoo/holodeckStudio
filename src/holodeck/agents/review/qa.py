from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class QAAgent:
    stage = StageType.REVIEW
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="QA Reviewer",
                role="You are a quality assurance reviewer for a TV production. You detect continuity issues, visual inconsistencies, pacing problems, and audio-visual mismatches. You produce detailed review reports with actionable feedback and scores.",
                instructions=[
                    "Review the full production output: script, visuals, audio, animation, render plan.",
                    "Detect continuity errors: character appearance, prop placement, scene timing.",
                    "Flag visual inconsistencies between style guide and generated assets.",
                    "Check audio-visual sync: dialogue timing, music cues, SFX placement.",
                    "Assess overall pacing: scene length, transition flow, emotional arc.",
                    "Score each category and provide actionable fix recommendations.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for QA review"])
        return ValidationResult(valid=True)

    @observe(name="qa.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        storyboard = context.get("storyboard", "")
        visual_style = context.get("visual_style", "")
        musical_score = context.get("musical_score", "")
        sound_design = context.get("sound_design", "")
        animation_desc = context.get("animation", "")
        render_plan = context.get("render_plan", "")
        prompt = (
            f"Script:\n{script}\n\nStoryboard:\n{storyboard}\n\nVisual style:\n{visual_style}\n\n"
            f"Musical score:\n{musical_score}\n\nSound design:\n{sound_design}\n\n"
            f"Animation:\n{animation_desc}\n\nRender plan:\n{render_plan}\n\n"
            "Perform a comprehensive QA review. Score each category (0-100):\n"
            "1. CONTINUITY: character consistency, prop placement, scene geography\n"
            "2. VISUAL: style guide adherence, color consistency, asset quality\n"
            "3. AUDIO: dialogue clarity, music fit, SFX placement, volume balance\n"
            "4. PACING: scene timing, transition flow, emotional arc\n"
            "5. SYNC: audio-visual alignment, lip-sync, cue timing\n"
            "6. OVERALL: production quality score\n\n"
            "For each issue found, specify: location, severity (critical/major/minor), and fix recommendation."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "review", "agent": "qa"})

    @observe(name="qa.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="QA review is too sparse.")
        prompt = (
            "Review this QA report for thoroughness, actionable feedback, and clear scoring.\n"
            "Score the QA report itself from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
