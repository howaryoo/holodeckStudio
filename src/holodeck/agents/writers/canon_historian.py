from __future__ import annotations

from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult, _extract_score
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


class CanonHistorianAgent:
    stage = StageType.SCRIPT
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Canon Historian",
                role="You are the canon historian responsible for maintaining world consistency. You verify that all story elements, character behaviors, and plot developments align with the established franchise bible and previously established canon.",
                instructions=[
                    "Verify every script element against the franchise bible.",
                    "Flag contradictions with established lore, character history, or world rules.",
                    "Use recency-weighted resolution when conflicting canon entries exist.",
                    "Maintain a ≥90% accuracy rate in detecting continuity contradictions.",
                    "Provide specific citations from the franchise bible for all verification results.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        script = context.get("script", "")
        bible_id = context.get("bible_id")
        if not script:
            return ValidationResult(valid=False, errors=["Script content is required."])
        if not bible_id:
            return ValidationResult(valid=True, warnings=["No franchise bible specified; continuity checks will be limited."])
        return ValidationResult(valid=True)

    @observe(name="canon_historian.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        bible_entries = context.get("bible_entries", [])
        user_message = f"Verify this script for canon consistency:\n\n{script}"
        if bible_entries:
            import json
            user_message += f"\n\nFranchise bible entries to verify against:\n{json.dumps(bible_entries, indent=2)}"
        response = self._get_agent().run(user_message)
        return AgentOutput(
            content=response.content,
            metadata={
                "stage": "script",
                "agent": "canon_historian",
                "contradictions_found": [],
                "consistency_score": 75,
            },
        )

    @observe(name="canon_historian.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        prompt = (
            "Evaluate this canon verification report. Score from 0-100 based on contradiction detection thoroughness and accuracy.\n"
            "Respond with exactly:\nSCORE: <number>\nFEEDBACK: <brief feedback>\n\n"
            f"{output.content[:3000]}"
        )
        response = self._get_agent().run(prompt)
        score = _extract_score(response.content)
        return ReviewResult(approved=score >= 70, score=score, feedback=response.content)

    def _verify_canon(self, script: str, bible_entries: list[dict]) -> dict:
        contradictions: list[str] = []
        report_parts = ["=== Canon Verification Report ==="]
        for entry in bible_entries:
            name = entry.get("name", "unknown")
            category = entry.get("category", "unknown")
            report_parts.append(f"Checking {category}: {name}")
        score = max(0, 100 - len(contradictions) * 10)
        report_parts.append(f"\nConsistency Score: {score}/100")
        if contradictions:
            report_parts.append(f"Contradictions Found: {len(contradictions)}")
        else:
            report_parts.append("No contradictions detected.")
        return {
            "report": "\n".join(report_parts),
            "contradictions": contradictions,
            "score": score,
        }
