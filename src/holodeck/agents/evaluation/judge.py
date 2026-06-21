from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult
from holodeck.evaluation.schemas import DimensionScore, EvaluationDimension
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


def _build_system_prompt() -> str:
    dims = EvaluationDimension.DIMENSIONS
    dim_block = "\n\n".join(
        f"### {name}\n"
        f"Description: {meta['description']}\n"
        f"Weight: {meta['weight']}\n"
        f"Signals (look for these):\n"
        + "\n".join(f"  - {s}" for s in meta["signals"])
        + "\nRed flags (trigger if present):\n"
        + "\n".join(f"  - {r}" for r in meta["red_flags"])
        for name, meta in dims.items()
    )

    return f"""You are a Judge agent that evaluates sitcom scripts against a franchise bible.

Given a generated script and the quality guidelines it was meant to satisfy, you score
the script across exactly 8 evaluation dimensions.

## Evaluation Dimensions

{dim_block}

## Output Format

Respond with a JSON array of exactly 8 objects, one per dimension, in this order:
narrative_coherence, character_consistency, comedy_effectiveness, dialogue_naturalness,
story_structure, emotional_impact, production_feasibility, thematic_alignment.

Each object must have:
{{
  "dimension": "<dimension_name>",
  "score": <float 0.0-1.0>,
  "weight": <float from the dimension definition above>,
  "reasoning": "<1-3 sentence explanation>",
  "evidence": ["<direct quote or observation from script>", ...]
}}

Return ONLY the JSON array. No markdown, no preamble, no trailing text.
"""


def _parse_dimension_scores(content: str) -> list[DimensionScore]:
    json_match = re.search(r"\[.*\]", content, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON array found in JudgeAgent response: {content[:200]}")

    raw: list[dict] = json.loads(json_match.group())
    if len(raw) != 8:
        raise ValueError(f"Expected 8 dimension scores, got {len(raw)}")

    return [DimensionScore(**item) for item in raw]


class JudgeAgent:
    stage = StageType.REVIEW
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Judge",
                role="Script quality judge for sitcom evaluation",
                instructions=[_build_system_prompt()],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("content"):
            return ValidationResult(valid=False, errors=["Script content is required"])
        if not context.get("guidelines"):
            return ValidationResult(valid=False, errors=["Quality guidelines are required"])
        return ValidationResult(valid=True)

    @observe(name="judge.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context["content"]
        guidelines = context["guidelines"]

        user_message = (
            f"## Quality Guidelines\n{json.dumps(guidelines, indent=2)}\n\n"
            f"## Generated Script\n{script}\n\n"
            "Score this script across all 8 evaluation dimensions."
        )

        response = self._get_agent().run(user_message)
        raw_content: str = response.content if hasattr(response, "content") else str(response)

        dimension_scores = _parse_dimension_scores(raw_content)

        return AgentOutput(
            content=raw_content,
            metadata={"dimension_scores": [ds.model_dump() for ds in dimension_scores]},
        )

    @observe(name="judge.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        scores = output.metadata.get("dimension_scores", [])
        if len(scores) != 8:
            return ReviewResult(approved=False, score=0, feedback="Incomplete dimension scores")
        avg = sum(s["score"] * s["weight"] for s in scores)
        score_int = int(avg * 100)
        return ReviewResult(
            approved=avg >= 0.35,
            score=score_int,
            feedback=f"Overall weighted score: {avg:.3f}",
        )
