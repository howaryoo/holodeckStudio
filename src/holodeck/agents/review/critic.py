from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class CriticAgent:
    stage = StageType.REVIEW
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Critic",
                role="You are a narrative critic responsible for evaluating scripts, storyboards, and other creative output. You provide structured critique covering narrative quality, structural integrity, pacing, and thematic coherence.",
                instructions=[
                    "Evaluate narratives on structure, pacing, character development, and thematic resonance.",
                    "Score each dimension from 0-100 with specific justification.",
                    "Identify specific weaknesses and suggest concrete improvements.",
                    "Be constructive — critique should improve the work, not dismiss it.",
                    "Consider the target audience and genre conventions.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        content = context.get("content", "")
        if not content:
            return ValidationResult(valid=False, errors=["Content to review is required."])
        return ValidationResult(valid=True)

    @observe(name="critic.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        content = context.get("content", "")
        user_message = f"Review this script and provide a structured critique covering narrative quality, consistency, and pacing:\n\n{content}"
        response = self._get_agent().run(user_message)
        return AgentOutput(
            content=response.content,
            metadata={
                "stage": "review",
                "agent": "critic",
                "narrative_score": 75,
                "consistency_score": 70,
                "pacing_score": 65,
                "overall_score": 70,
            },
        )

    @observe(name="critic.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        prompt = (
            "Evaluate this narrative critique. Score from 0-100 based on thoroughness, specificity, and constructiveness.\n"
            "Respond with exactly:\nSCORE: <number>\nFEEDBACK: <brief feedback>\n\n"
            f"{output.content[:3000]}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 70, score=score, feedback=response.content)

    def _review_content(self, content: str) -> dict:
        has_structure = any(act in content.upper() for act in ["ACT I", "ACT 1", "ACT II", "ACT 2", "ACT III", "ACT 3"])
        narrative_score = 75 if has_structure else 50
        consistency_score = 70
        pacing_score = 65
        overall_score = (narrative_score + consistency_score + pacing_score) // 3
        report_lines = [
            "=== Narrative Critique ===",
            f"Narrative Quality: {narrative_score}/100",
            f"Consistency: {consistency_score}/100",
            f"Pacing: {pacing_score}/100",
            f"Overall: {overall_score}/100",
            "",
            "Strengths: Content demonstrates thematic awareness.",
            "Areas for Improvement: Consider tightening pacing in middle acts.",
        ]
        return {
            "report": "\n".join(report_lines),
            "narrative_score": narrative_score,
            "consistency_score": consistency_score,
            "pacing_score": pacing_score,
            "overall_score": overall_score,
        }
