from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class EnvironmentDesignerAgent:
    stage = StageType.ASSET_GENERATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Environment Designer",
                role="You design environments and locations from the script consistent with the production's visual style. You create detailed architectural and environmental concept descriptions.",
                instructions=[
                    "Design environments based on script scene descriptions and creative direction.",
                    "Follow the Production Designer's architectural and color style guide.",
                    "Describe spatial layout, scale, lighting, materials, and atmosphere.",
                    "Consider how characters move through and interact with the environment.",
                    "Design exterior and interior views where applicable.",
                    "Ensure environments serve the narrative and emotional tone of each scene.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for environment design"])
        return ValidationResult(valid=True)

    @observe(name="environment_designer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        style_guide = context.get("visual_style", "")
        direction = context.get("visual_direction", "")
        prompt = (
            f"Script:\n{script}\n\nVisual style guide:\n{style_guide}\n\n"
            f"Visual direction:\n{direction}\n\n"
            "Design each location. For each:\n"
            "LOCATION: <name>\n"
            "- TYPE: interior/exterior, architectural style\n"
            "- LAYOUT: spatial description, key areas, paths\n"
            "- LIGHTING: natural/artificial, color temperature, mood\n"
            "- MATERIALS: surfaces, textures, colors\n"
            "- ATMOSPHERE: temperature, sounds, smells, time of day\n"
            "- SCALE: size relative to characters\n"
            "- INTERACTION: how characters navigate and interact\n"
            "Be detailed and consistent with the established visual style."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "asset_generation", "agent": "environment_designer"})

    @observe(name="environment_designer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Environment design is too sparse.")
        prompt = (
            "Review these environment designs for spatial detail, atmospheric quality, and consistency with the style guide.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
