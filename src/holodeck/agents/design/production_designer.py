from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class ProductionDesignerAgent:
    stage = StageType.ASSET_GENERATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Production Designer",
                role="You define the overall visual style of the production: color palette, lighting philosophy, architectural themes, costume aesthetics, and prop design language. You ensure artistic consistency across all visual outputs.",
                instructions=[
                    "Define the visual style guide: color palette, textures, lighting approach.",
                    "Establish architectural and environmental design language.",
                    "Define costume and prop aesthetic consistent with the story's setting and tone.",
                    "Provide reference descriptions for Character Designer and Environment Designer.",
                    "Ensure all visual elements feel cohesive and support the narrative.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for visual style definition"])
        return ValidationResult(valid=True)

    @observe(name="production_designer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        creative = context.get("creative_direction", "")
        prompt = (
            f"Script:\n{script}\n\nCreative direction:\n{creative}\n\n"
            "Define the visual production style:\n"
            "- COLOR PALETTE: primary, secondary, accent colors with hex codes\n"
            "- LIGHTING: key light style, mood, shadows\n"
            "- ARCHITECTURE: building styles, materials, scale\n"
            "- COSTUME: era, materials, silhouettes, color rules\n"
            "- PROPS: design language, materials, scale\n"
            "Be specific and descriptive."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "asset_generation", "agent": "production_designer"})

    @observe(name="production_designer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Style guide is too vague.")
        prompt = (
            "Review this visual style guide for specificity, coherence, and coverage of all visual domains.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
