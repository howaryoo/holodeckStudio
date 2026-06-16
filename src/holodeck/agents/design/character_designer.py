from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class CharacterDesignerAgent:
    stage = StageType.ASSET_GENERATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Character Designer",
                role="You design character appearances consistent with the production's visual style. You create detailed character sheets describing appearance, costumes, expressions, and silhouettes.",
                instructions=[
                    "Design characters based on script descriptions and creative direction.",
                    "Follow the Production Designer's style guide for colors, materials, and aesthetic.",
                    "Create detailed appearance descriptions: body type, face, hair, distinctive features.",
                    "Design costume variations for key scenes and emotional states.",
                    "Describe expression range: neutral, happy, angry, frightened, surprised, sad.",
                    "Ensure characters are visually distinct and consistent with their personality.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for character design"])
        return ValidationResult(valid=True)

    @observe(name="character_designer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        style_guide = context.get("visual_style", "")
        prompt = (
            f"Script:\n{script}\n\nVisual style guide:\n{style_guide}\n\n"
            "Design each character. For each:\n"
            "CHARACTER: <name>\n"
            "- BODY: height, build, posture, distinguishing features\n"
            "- FACE: shape, eyes, nose, mouth, skin tone, age\n"
            "- HAIR: style, color, length\n"
            "- COSTUME: primary outfit, materials, colors, accessories\n"
            "- EXPRESSIONS: neutral, happy, angry, frightened, surprised\n"
            "- SILHOUETTE: distinctive shape description\n"
            "Be detailed and consistent with the established visual style."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "asset_generation", "agent": "character_designer"})

    @observe(name="character_designer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Character design is too sparse.")
        prompt = (
            "Review these character designs for detail, visual distinctiveness, and consistency with the style guide.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
