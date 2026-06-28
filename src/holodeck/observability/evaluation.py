from __future__ import annotations

from typing import Any
from uuid import UUID

from holodeck.config.settings import Settings


class EvaluationTracker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._prompt_versions: dict[str, str] = {}
        self._cost_records: list[dict[str, Any]] = []
        self._performance_records: list[dict[str, Any]] = []

    def record_prompt_version(self, agent_role: str, version: str) -> None:
        self._prompt_versions[agent_role] = version

    def get_prompt_version(self, agent_role: str) -> str | None:
        return self._prompt_versions.get(agent_role)

    def record_cost(
        self,
        production_id: UUID | str,
        stage: str,
        agent_role: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> dict[str, Any]:
        record = {
            "production_id": str(production_id),
            "stage": stage,
            "agent_role": agent_role,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }
        self._cost_records.append(record)
        self._try_langfuse_cost(record)
        return record

    def _try_langfuse_cost(self, record: dict[str, Any]) -> None:
        try:
            from holodeck.observability.tracing import get_client
            client = get_client()
            if client is not None:
                client.cost(
                    trace_id=record["production_id"],
                    name=f"{record['agent_role']}_{record['stage']}",
                    input_cost=record.get("input_tokens", 0) * 0.000001,
                    output_cost=record.get("output_tokens", 0) * 0.000002,
                    usage={
                        "input": record.get("input_tokens", 0),
                        "output": record.get("output_tokens", 0),
                    },
                )
        except Exception:
            pass

    def get_total_cost(self) -> float:
        return sum(r["cost_usd"] for r in self._cost_records)

    def record_agent_performance(
        self,
        agent_role: str,
        stage: str,
        quality_score: int,
        duration_seconds: float,
    ) -> dict[str, Any]:
        record = {
            "agent_role": agent_role,
            "stage": stage,
            "quality_score": quality_score,
            "duration_seconds": duration_seconds,
        }
        self._performance_records.append(record)
        return record

    def get_performance_summary(self) -> dict[str, Any]:
        if not self._performance_records:
            return {}
        by_agent: dict[str, list[int]] = {}
        for r in self._performance_records:
            by_agent.setdefault(r["agent_role"], []).append(r["quality_score"])
        return {
            agent: {
                "avg_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "runs": len(scores),
            }
            for agent, scores in sorted(by_agent.items())
        }

    def get_cost_summary(self) -> dict[str, Any]:
        if not self._cost_records:
            return {}
        by_agent: dict[str, float] = {}
        for r in self._cost_records:
            by_agent[r["agent_role"]] = by_agent.get(r["agent_role"], 0) + r["cost_usd"]
        return {
            "total_usd": self.get_total_cost(),
            "by_agent": by_agent,
            "by_stage": {
                stage: sum(r["cost_usd"] for r in self._cost_records if r["stage"] == stage)
                for stage in {r["stage"] for r in self._cost_records}
            },
        }
