from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class HeadWriterAgent:
    stage = StageType.SCRIPT
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Head Writer",
                role="You are the head writer of a TV production studio. You generate season arcs, approve episode concepts, and revise scripts for narrative quality, pacing, and thematic alignment.",
                instructions=[
                    "Generate compelling narratives that serve the showrunner's creative vision.",
                    "Revise drafts for narrative quality: pacing, dialogue, character arcs, and thematic resonance.",
                    "Ensure each episode has a clear three-act structure.",
                    "Approve scripts only when they meet quality standards.",
                    "Provide specific, actionable feedback on rejected drafts.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        creative_direction = context.get("creative_direction", "")
        if not creative_direction:
            return ValidationResult(valid=False, errors=["Creative direction from Showrunner is required."])
        return ValidationResult(valid=True)

    @observe(name="head_writer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        creative_direction = context.get("creative_direction", "")
        outline = context.get("outline", "")
        user_message = f"Write a complete script based on this creative direction:\n\n{creative_direction}"
        if outline:
            user_message += f"\n\nOutline to follow:\n{outline}"
        response = self._get_agent().run(user_message)
        return AgentOutput(
            content=response.content,
            metadata={"stage": "script", "agent": "head_writer"},
        )

    @observe(name="head_writer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content) < 100:
            return ReviewResult(approved=False, score=0, feedback="Script is too short or empty.")
        prompt = (
            "Review this script. Score from 0-100 based on narrative quality, pacing, character development, and structure.\n"
            "Respond with exactly:\nSCORE: <number>\nFEEDBACK: <brief feedback>\n\n"
            f"{output.content[:3000]}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 70, score=score, feedback=response.content)

    def _generate_script(self, creative_direction: str, outline: str = "") -> str:
        parts = [
            "=== SCRIPT ===",
            f"Based on: {creative_direction[:200]}",
            "",
            "ACT I - SETUP",
            "[Scene descriptions establishing characters, setting, and initial conflict]",
            "",
            "ACT II - CONFRONTATION",
            "[Rising action, character development, complications]",
            "",
            "ACT III - RESOLUTION",
            "[Climax, character growth, thematic conclusion]",
            "",
            "=== END SCRIPT ===",
        ]
        if outline:
            parts.insert(1, f"Outline reference: {outline[:100]}")
        return "\n".join(parts)
