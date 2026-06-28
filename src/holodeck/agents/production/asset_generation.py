from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class AssetGenerationAgent:
    stage = StageType.ASSET_GENERATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Asset Generator",
                role="You generate detailed image asset descriptions, character art specs, background art descriptions, and prop designs from storyboard frames. Your descriptions are precise enough for a concept artist or AI image generator to execute.",
                instructions=[
                    "Read storyboard frame descriptions and extract visual asset requirements.",
                    "Generate character art specs: pose, expression, costume, lighting, angle.",
                    "Generate background/environment art specs: location, time of day, weather, mood.",
                    "Generate prop and object specs: design, materials, scale, placement.",
                    "Describe each asset with camera framing, composition, and color palette.",
                    "Ensure all assets are consistent with the established visual style guide.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("storyboard"):
            return ValidationResult(valid=False, errors=["Storyboard required for asset generation"])
        return ValidationResult(valid=True)

    @observe(name="asset_generation.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        storyboard = context.get("storyboard", "")
        style_guide = context.get("visual_style", "")
        character_sheets = context.get("character_designs", "")
        prompt = (
            f"Storyboard:\n{storyboard}\n\nVisual style guide:\n{style_guide}\n\n"
            f"Character designs:\n{character_sheets}\n\n"
            "Generate image asset descriptions. For each asset:\n"
            "ASSET: <type> - <subject>\n"
            "- DESCRIPTION: detailed visual description\n"
            "- STYLE: consistent with production style guide\n"
            "- COMPOSITION: framing, camera angle, depth\n"
            "- COLOR: palette, lighting, shadows\n"
            "- CHARACTER: expression, pose, costume if applicable\n"
            "- BACKGROUND: environment, props, atmosphere\n"
            "Group by category: characters, environments, props, keyframes."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content, metadata={"stage": "asset_generation", "agent": "asset_generation"})

    @observe(name="asset_generation.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, score=0, feedback="Asset descriptions are too sparse.")
        prompt = (
            "Review these asset generation descriptions for visual detail, consistency with the style guide, and coverage of all storyboard elements.\n"
            "Score from 0-100.\nRespond with:\nSCORE: <number>\nFEEDBACK: <brief>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)
