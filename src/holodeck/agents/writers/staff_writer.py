from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class StaffWriterAgent:
    stage = StageType.SCRIPT
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Staff Writer",
                role="You are a staff writer responsible for drafting scenes, generating dialogue, and proposing story ideas. You work under the Head Writer's supervision.",
                instructions=[
                    "Draft scenes with vivid, character-specific dialogue.",
                    "Follow the narrative direction set by the Head Writer.",
                    "Propose story ideas that align with the established creative vision.",
                    "Revise drafts based on feedback from the Head Writer.",
                    "Ensure dialogue is natural and serves character development.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        scene_direction = context.get("scene_direction", "")
        if not scene_direction:
            return ValidationResult(valid=True, warnings=["No scene direction provided; improvising."])
        return ValidationResult(valid=True)

    @observe(name="staff_writer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        scene_direction = context.get("scene_direction", "")
        characters = context.get("characters", [])
        user_message = f"Write detailed scenes and dialogue based on this direction:\n\n{scene_direction}"
        if characters:
            char_list = "\n".join(c.get("name", "Unknown") for c in characters[:5])
            user_message += f"\n\nCharacters:\n{char_list}"
        response = self._get_agent().run(user_message)
        return AgentOutput(
            content=response.content,
            metadata={"stage": "script", "agent": "staff_writer"},
        )

    @observe(name="staff_writer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 20:
            return ReviewResult(approved=False, feedback="Scene draft is too short.")
        prompt = (
            "Review this scene draft. Score from 0-100 based on dialogue quality, scene structure, and character voice.\n"
            "Respond with exactly:\nSCORE: <number>\nFEEDBACK: <brief feedback>\n\n"
            f"{output.content[:3000]}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 65, score=score, feedback=response.content)

    def _draft_scene(self, scene_direction: str, characters: list[dict]) -> str:
        parts = [
            "=== SCENE DRAFT ===",
            f"Scene direction: {scene_direction[:200]}" if scene_direction else "Improvised scene",
        ]
        if characters:
            char_names = ", ".join(c.get("name", "Unknown") for c in characters[:3])
            parts.append(f"Characters: {char_names}")
        parts.extend([
            "",
            "[Character dialogue and action descriptions]",
            "",
            "=== END SCENE ===",
        ])
        return "\n".join(parts)
