from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class AudienceSimulationAgent:
    stage = StageType.REVIEW
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Audience Simulator",
                role="You simulate audience reactions to a TV production across multiple viewer segments: science-fiction fans, casual viewers, critics, and franchise loyalists. You predict emotional responses, engagement levels, and potential controversies.",
                instructions=[
                    "Analyze the script, visual design, and audio for each audience segment.",
                    "Science-fiction fans: rate originality, world-building, tech plausibility, genre tropes.",
                    "Casual viewers: rate entertainment value, emotional engagement, clarity, pacing.",
                    "Critics: rate thematic depth, character development, directorial vision, cultural relevance.",
                    "Franchise fans: rate canon consistency, character faithfulness, lore expansion.",
                    "Provide an overall projected audience score with segment breakdowns.",
                    "Flag potential controversy or divisive elements.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for audience simulation"])
        return ValidationResult(valid=True)

    @observe(name="audience_simulation.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        visual_style = context.get("visual_style", "")
        musical_score = context.get("musical_score", "")
        prompt = (
            f"Script:\n{script}\n\nVisual style:\n{visual_style}\n\n"
            f"Musical score:\n{musical_score}\n\n"
            "Simulate audience reactions across four segments:\n\n"
            "1. SCI-FI FANS (score 0-100):\n"
            "- World-building originality, tech/sci-fi plausibility, genre trope handling\n\n"
            "2. CASUAL VIEWERS (score 0-100):\n"
            "- Entertainment value, emotional engagement, clarity of story, pacing\n\n"
            "3. CRITICS (score 0-100):\n"
            "- Thematic depth, character development, directorial vision, cultural relevance\n\n"
            "4. FRANCHISE LOYALISTS (score 0-100):\n"
            "- Canon consistency, character faithfulness, lore expansion\n\n"
            "For each segment, provide:\n"
            "SEGMENT: <name>\n"
            "SCORE: <0-100>\n"
            "REACTION: <paragraph describing likely audience reaction>\n"
            "PRAISE: <what this segment would love>\n"
            "CRITIQUE: <what this segment would criticize>\n\n"
            "Then provide:\n"
            "OVERALL PROJECTED SCORE: <0-100>\n"
            "CONTROVERSY FLAG: <yes/no> - <explanation if yes>\n"
            "RECOMMENDATION: <targeted adjustment to improve reception>"
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "review", "agent": "audience_simulation"})

    @observe(name="audience_simulation.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Audience simulation is too sparse.")
        prompt = (
            "Review this audience simulation for depth of segment analysis, specificity of reactions, and actionable recommendations.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
