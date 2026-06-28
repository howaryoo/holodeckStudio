from __future__ import annotations

from typing import Any

from holodeck.pipeline.stages import StageType, ProductionMode, get_revision_target
from holodeck.pipeline.events import (
    ProductionStarted,
    StageStarted,
    StageCompleted,
    StageAwaitingApproval,
    StageApproved,
    StageRejected,
    RevisionRequested,
    ConflictDetected,
    ConflictResolved,
    ProductionCompleted,
    ProductionFailed,
    AsyncioEventBus,
)


class PipelineOrchestrator:
    def __init__(
        self,
        event_bus: AsyncioEventBus,
        max_feedback_iterations: int = 3,
        conflict_escalation_threshold: int = 3,
        quality_gate_threshold: int = 70,
    ) -> None:
        self._event_bus = event_bus
        self._max_feedback_iterations = max_feedback_iterations
        self._conflict_escalation_threshold = conflict_escalation_threshold
        self._quality_gate_threshold = quality_gate_threshold
        self._conflict_counts: dict[str, int] = {}
        self._stage_iterations: dict[str, int] = {}

    async def start_production(self, production_id: Any, theme_prompt: str, mode: str = "autonomous") -> None:
        await self._event_bus.publish(
            ProductionStarted(
                event_type="production.started",
                production_id=production_id,
                theme_prompt=theme_prompt,
                mode=mode,
                config={
                    "max_feedback_iterations": self._max_feedback_iterations,
                    "conflict_escalation_threshold": self._conflict_escalation_threshold,
                    "quality_gate_threshold": self._quality_gate_threshold,
                },
            )
        )

    async def start_stage(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        stage_type: StageType,
        agent_role: str,
        iteration: int = 0,
    ) -> None:
        print(f"  Stage: {agent_role} ({stage_type.value})...", flush=True)
        await self._event_bus.publish(
            StageStarted(
                event_type="stage.started",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                stage_type=stage_type.value,
                agent_role=agent_role,
                iteration=iteration,
            )
        )

    async def complete_stage(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        stage_type: StageType,
        agent_role: str,
        output_assets: list[Any] | None = None,
        quality_score: int = 0,
    ) -> None:
        print(f"  Done: {agent_role}", flush=True)
        await self._event_bus.publish(
            StageCompleted(
                event_type="stage.completed",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                stage_type=stage_type.value,
                agent_role=agent_role,
                output_assets=output_assets or [],
                quality_score=quality_score,
            )
        )

    async def checkpoint_approval(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        stage_type: StageType,
        mode: str = "autonomous",
        quality_score: int = 0,
        timeout_seconds: int = 300,
    ) -> bool:
        if mode == ProductionMode.SUPERVISED.value or mode == "supervised":
            from datetime import datetime, timedelta
            timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
            await self._event_bus.publish(
                StageAwaitingApproval(
                    event_type="stage.awaiting_approval",
                    production_id=production_id,
                    episode_id=episode_id,
                    stage_id=stage_id,
                    stage_type=stage_type.value,
                    timeout_at=timeout_at,
                )
            )
            return False
        if quality_score >= self._quality_gate_threshold:
            await self._event_bus.publish(
                StageApproved(
                    event_type="stage.approved",
                    production_id=production_id,
                    episode_id=episode_id,
                    stage_id=stage_id,
                    stage_type=stage_type.value,
                    checkpoint_id=stage_id,
                    reviewer="auto",
                    note=f"Auto-approved (score {quality_score} >= threshold {self._quality_gate_threshold})",
                )
            )
            return True
        await self._event_bus.publish(
            StageAwaitingApproval(
                event_type="stage.awaiting_approval",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                stage_type=stage_type.value,
                timeout_at=None,
            )
        )
        return False

    async def request_approval(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        stage_type: StageType,
        timeout_seconds: int | None = None,
    ) -> None:
        from datetime import datetime, timedelta
        timeout_at = None
        if timeout_seconds:
            timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        await self._event_bus.publish(
            StageAwaitingApproval(
                event_type="stage.awaiting_approval",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                stage_type=stage_type.value,
                timeout_at=timeout_at,
            )
        )

    async def approve_stage(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        stage_type: StageType,
        reviewer: str = "auto",
        note: str | None = None,
    ) -> None:
        await self._event_bus.publish(
            StageApproved(
                event_type="stage.approved",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                stage_type=stage_type.value,
                checkpoint_id=stage_id,
                reviewer=reviewer,
                note=note,
            )
        )

    async def reject_stage(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        stage_type: StageType,
        reviewer: str,
        feedback: str,
    ) -> None:
        stage_key = stage_type.value
        iteration = self._stage_iterations.get(stage_key, 0) + 1
        self._stage_iterations[stage_key] = iteration

        if iteration > self._max_feedback_iterations:
            await self._event_bus.publish(
                ProductionFailed(
                    event_type="production.failed",
                    production_id=production_id,
                    episode_id=episode_id,
                    stage_id=stage_id,
                    error_stage=stage_type.value,
                    error_agent=reviewer,
                    error_message=f"Max iterations ({self._max_feedback_iterations}) exceeded for stage {stage_type.value}",
                    recoverable=False,
                )
            )
            return

        revision_target = get_revision_target(stage_type)
        if revision_target:
            await self._event_bus.publish(
                RevisionRequested(
                    event_type="agent.revision_requested",
                    production_id=production_id,
                    episode_id=episode_id,
                    stage_id=stage_id,
                    requesting_agent=reviewer,
                    target_agent="upstream",
                    target_stage=revision_target.value,
                    feedback=feedback,
                )
            )

        await self._event_bus.publish(
            StageRejected(
                event_type="stage.rejected",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                stage_type=stage_type.value,
                checkpoint_id=stage_id,
                reviewer=reviewer,
                feedback=feedback,
            )
        )

    async def detect_conflict(
        self,
        production_id: Any,
        episode_id: Any,
        stage_id: Any,
        agent_a: str,
        agent_b: str,
        description: str,
    ) -> None:
        conflict_key = f"{agent_a}:{agent_b}"
        count = self._conflict_counts.get(conflict_key, 0) + 1
        self._conflict_counts[conflict_key] = count

        await self._event_bus.publish(
            ConflictDetected(
                event_type="agent.conflict_detected",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                agent_a=agent_a,
                agent_b=agent_b,
                conflict_description=description,
                conflict_count=count,
            )
        )

        if count >= self._conflict_escalation_threshold:
            await self._event_bus.publish(
                ConflictResolved(
                    event_type="agent.conflict_resolved",
                    production_id=production_id,
                    episode_id=episode_id,
                    stage_id=stage_id,
                    resolving_authority="human",
                    resolution=f"Escalated after {count} conflicts between {agent_a} and {agent_b}",
                    escalation_threshold_reached=True,
                )
            )

    async def fail_production(
        self,
        production_id: Any,
        episode_id: Any | None,
        stage_id: Any | None,
        error_stage: str,
        error_agent: str,
        error_message: str,
        recoverable: bool = False,
    ) -> None:
        await self._event_bus.publish(
            ProductionFailed(
                event_type="production.failed",
                production_id=production_id,
                episode_id=episode_id,
                stage_id=stage_id,
                error_stage=error_stage,
                error_agent=error_agent,
                error_message=error_message,
                recoverable=recoverable,
            )
        )

    async def complete_production(
        self,
        production_id: Any,
        output_path: str,
        total_cost_usd: float = 0.0,
        total_duration_seconds: float = 0.0,
    ) -> None:
        from decimal import Decimal
        await self._event_bus.publish(
            ProductionCompleted(
                event_type="production.completed",
                production_id=production_id,
                output_path=output_path,
                total_cost_usd=Decimal(str(total_cost_usd)),
                total_duration_seconds=total_duration_seconds,
            )
        )