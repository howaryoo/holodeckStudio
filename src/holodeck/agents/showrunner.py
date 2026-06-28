from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agno.agent import Agent

from holodeck.agents.base import (
    AgentOutput,
    ReviewResult,
    StageType,
    ValidationResult,
    _extract_score,
)
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class ShowrunnerAgent:
    stage = StageType.CONCEPT
    _agent: Agent | None = None
    _conflict_count: int = 0

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Showrunner",
                role="You are the showrunner of a TV production studio. You own the creative vision, maintain consistency across all departments, and resolve disagreements between agents. You make final decisions on creative direction.",
                instructions=[
                    "Maintain the overall creative vision for the production.",
                    "Resolve conflicts between agents with clear, documented rationale.",
                    "Approve progression between production stages only when quality gates are met.",
                    "Escalate to human operator when conflict frequency exceeds the threshold.",
                    "Ensure canon consistency across all departments.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        theme_prompt = context.get("theme_prompt", "")
        if not theme_prompt or len(theme_prompt.strip()) < 20:
            return ValidationResult(
                valid=False,
                errors=["Theme prompt must be at least 20 characters."],
            )
        return ValidationResult(valid=True)

    @observe(name="showrunner.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        theme_prompt = context.get("theme_prompt", "")
        previous_conflicts = context.get("conflict_history", [])
        user_message = theme_prompt
        if previous_conflicts:
            user_message += f"\n\nResolve these prior conflicts in your creative direction:\n{previous_conflicts}"
        use_agent_cache = context.get("use_cache", True)
        from holodeck.cache import cached_agent_run
        response = cached_agent_run(
            self._get_agent().run,
            role="showrunner",
            user_message=user_message,
            use_cache=use_agent_cache,
        )
        return AgentOutput(
            content=response.content,
            metadata={"stage": "concept", "agent": "showrunner"},
        )

    @observe(name="showrunner.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        if not output.content or len(output.content.strip()) < 10:
            return ReviewResult(approved=False, feedback="Creative direction is too vague or empty.")
        prompt = (
            "Review this creative direction. Score from 0-100 based on specificity, coherence, and originality.\n"
            "Respond with exactly:\nSCORE: <number>\nFEEDBACK: <brief feedback>\n\n"
            f"{output.content}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 70, score=score, feedback=response.content)

    def resolve_conflict(
        self,
        agent_a: str,
        agent_b: str,
        conflict_description: str,
        escalation_threshold: int = 3,
    ) -> dict[str, Any]:
        self._conflict_count += 1
        resolution = f"Showrunner resolves conflict between {agent_a} and {agent_b}: {conflict_description}. Creative authority applied."
        escalated = self._conflict_count >= escalation_threshold
        return {
            "resolving_authority": "showrunner" if not escalated else "human",
            "resolution": resolution,
            "escalation_threshold_reached": escalated,
        }

    def _generate_creative_direction(self, prompt: str, conflicts: list) -> str:
        direction_parts = [
            f"Creative direction for: {prompt}",
            "Establish core themes, tone, and narrative arc.",
            "Define character relationships and development trajectories.",
            "Set visual and tonal standards for all departments.",
        ]
        if conflicts:
            direction_parts.append(f"Address {len(conflicts)} prior conflicts in creative vision.")
        return "\n".join(direction_parts)
