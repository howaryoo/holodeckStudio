from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class ProducerAgent:
    stage = StageType.REVIEW
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model
        self._budget_usd: float = 10.0
        self._spent_usd: float = 0.0

    def set_budget(self, budget_usd: float) -> None:
        self._budget_usd = budget_usd

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Producer",
                role="You are the producer of a TV production studio. You track resource costs, estimate budget for each production stage, and enforce spending limits. You flag budget overruns and suggest cost-saving alternatives.",
                instructions=[
                    "Estimate resource costs (tokens, compute) for each production stage.",
                    "Track cumulative spending against the allocated budget.",
                    "Alert when spending exceeds 80% of budget and pause at 100%.",
                    "Suggest cost-saving alternatives when budget is constrained.",
                    "Log all cost estimates and actuals for post-production analysis.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        return ValidationResult(valid=True)

    @observe(name="producer.estimate", as_type="generation")
    def estimate_stage_cost(self, stage: str, description: str) -> AgentOutput:
        prompt = (
            f"Estimate the LLM token cost for the '{stage}' production stage.\n"
            f"Description: {description}\n"
            "Consider input/output token counts, model tier, and complexity.\n"
            "Respond with a JSON object: {{\"estimated_tokens\": N, \"estimated_cost_usd\": X.X, \"confidence\": \"low|medium|high\"}}"
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content)

    @observe(name="producer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script_len = len(context.get("script", ""))
        budget = context.get("budget_usd", self._budget_usd)
        spent = context.get("total_cost_usd", self._spent_usd)
        agents_used = context.get("agent_executions", [])
        prompt = (
            f"Production budget: ${budget:.2f}\n"
            f"Amount spent so far: ${spent:.2f}\n"
            f"Script length: {script_len} characters\n"
            f"Agent executions: {len(agents_used)}\n\n"
            "Assess whether this production is within budget. If over 80%, suggest cost-saving measures. "
            "If over 100%, recommend pausing production."
        )
        response = self._get_agent().run(prompt)
        return AgentOutput(content=response.content)

    @observe(name="producer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        return ReviewResult(approved=True, score=100, feedback=output.content[:200])
