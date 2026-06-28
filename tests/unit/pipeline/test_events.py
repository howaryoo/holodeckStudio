from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from holodeck.pipeline.events import (
    AsyncioEventBus,
    ConflictDetected,
    ConflictResolved,
    ProductionCompleted,
    ProductionFailed,
    ProductionPaused,
    ProductionResumed,
    ProductionStarted,
    PromptRejected,
    QualityGateFailed,
    ReviewCompleted,
    RevisionRequested,
    StageApproved,
    StageAwaitingApproval,
    StageCompleted,
    StageIterationExceeded,
    StageRejected,
    StageStarted,
)


def _pid() -> UUID:
    return uuid4()


class TestEventModels:
    def test_production_started(self):
        pid = _pid()
        e = ProductionStarted(production_id=pid, theme_prompt="test", mode="autonomous", config={})
        assert e.event_type == "production.started"
        assert e.production_id == pid
        assert e.theme_prompt == "test"
        assert e.mode == "autonomous"

    def test_production_paused(self):
        e = ProductionPaused(production_id=_pid(), reason="budget")
        assert e.event_type == "production.paused"
        assert e.reason == "budget"

    def test_production_resumed(self):
        e = ProductionResumed(production_id=_pid())
        assert e.event_type == "production.resumed"

    def test_production_completed(self):
        e = ProductionCompleted(production_id=_pid(), output_path="/tmp")
        assert e.event_type == "production.completed"
        assert e.output_path == "/tmp"

    def test_production_failed(self):
        e = ProductionFailed(production_id=_pid(), error_stage="concept", error_agent="showrunner", error_message="fail")
        assert e.event_type == "production.failed"
        assert e.recoverable is False

    def test_stage_started(self):
        e = StageStarted(production_id=_pid(), stage_type="concept", agent_role="showrunner")
        assert e.event_type == "stage.started"
        assert e.iteration == 0

    def test_stage_completed(self):
        e = StageCompleted(production_id=_pid(), stage_type="concept", agent_role="showrunner", quality_score=85)
        assert e.event_type == "stage.completed"
        assert e.quality_score == 85

    def test_stage_awaiting_approval(self):
        e = StageAwaitingApproval(production_id=_pid(), stage_type="script")
        assert e.event_type == "stage.awaiting_approval"
        assert e.checkpoint_id is not None

    def test_stage_approved(self):
        e = StageApproved(production_id=_pid(), stage_type="script", checkpoint_id=uuid4(), reviewer="human")
        assert e.event_type == "stage.approved"

    def test_stage_rejected(self):
        e = StageRejected(production_id=_pid(), stage_type="script", checkpoint_id=uuid4(), reviewer="human", feedback="rewrite")
        assert e.event_type == "stage.rejected"
        assert e.feedback == "rewrite"

    def test_stage_iteration_exceeded(self):
        e = StageIterationExceeded(production_id=_pid(), stage_type="script", iteration_count=3, max_iterations=3)
        assert e.event_type == "stage.iteration_exceeded"
        assert e.iteration_count == 3

    def test_revision_requested(self):
        e = RevisionRequested(production_id=_pid(), requesting_agent="critic", target_agent="head_writer", target_stage="script", feedback="too slow")
        assert e.event_type == "agent.revision_requested"

    def test_conflict_detected(self):
        e = ConflictDetected(production_id=_pid(), agent_a="showrunner", agent_b="head_writer", conflict_description="tone")
        assert e.event_type == "agent.conflict_detected"
        assert e.conflict_count == 1

    def test_conflict_resolved(self):
        e = ConflictResolved(production_id=_pid(), resolving_authority="showrunner", resolution="go darker")
        assert e.event_type == "agent.conflict_resolved"
        assert e.escalation_threshold_reached is False

    def test_prompt_rejected(self):
        e = PromptRejected(production_id=_pid(), original_prompt="hi", rejection_reason="too_short", guidance="write more")
        assert e.event_type == "prompt.rejected"
        assert e.rejection_reason == "too_short"

    def test_review_completed(self):
        e = ReviewCompleted(production_id=_pid(), reviewer_type="critic", overall_score=80, passed=True)
        assert e.event_type == "review.completed"
        assert e.narrative_score == 0

    def test_quality_gate_failed(self):
        e = QualityGateFailed(production_id=_pid(), stage_type="script", overall_score=55, threshold=70)
        assert e.event_type == "review.quality_gate_failed"
        assert e.overall_score == 55

    def test_serialization_roundtrip(self):
        e = ProductionStarted(production_id=_pid(), theme_prompt="test", mode="autonomous", config={})
        data = e.model_dump()
        restored = ProductionStarted(**data)
        assert restored.event_type == e.event_type
        assert restored.production_id == e.production_id
        assert restored.theme_prompt == e.theme_prompt

    def test_episode_id_defaults_to_none(self):
        e = ProductionStarted(production_id=_pid(), theme_prompt="test", mode="autonomous", config={})
        assert e.episode_id is None

    def test_stage_id_defaults_to_none(self):
        e = StageStarted(production_id=_pid(), stage_type="concept", agent_role="showrunner")
        assert e.stage_id is None


@pytest.mark.asyncio
class TestAsyncioEventBus:
    async def test_publish_subscribe(self):
        bus = AsyncioEventBus()
        pid = _pid()
        events: list = []

        async def collector():
            async for e in bus.subscribe(["production.started"], production_id=pid):
                events.append(e)
                break

        async def publisher():
            await bus.publish(ProductionStarted(production_id=pid, theme_prompt="t", mode="autonomous", config={}))

        import asyncio
        await asyncio.gather(collector(), publisher())
        assert len(events) == 1
        assert events[0].event_type == "production.started"

    async def test_multiple_subscribers(self):
        bus = AsyncioEventBus()
        pid = _pid()
        results: list[list] = [[], []]

        async def sub(i):
            async for e in bus.subscribe(["stage.started"]):
                results[i].append(e)
                break

        async def pub():
            await bus.publish(StageStarted(production_id=pid, stage_type="concept", agent_role="showrunner"))

        import asyncio
        await asyncio.gather(sub(0), sub(1), pub())
        assert len(results[0]) == 1
        assert len(results[1]) == 1

    async def test_production_filtered_subscription(self):
        bus = AsyncioEventBus()
        pid1, pid2 = _pid(), _pid()
        received = []

        async def collector():
            async for e in bus.subscribe(["production.completed"]):
                received.append(e)
                if len(received) >= 2:
                    break

        async def publisher():
            await bus.publish(ProductionCompleted(production_id=pid2, output_path="/x"))
            await bus.publish(ProductionCompleted(production_id=pid1, output_path="/y"))

        import asyncio
        await asyncio.gather(collector(), publisher())
        assert len(received) == 2
        pids = {str(e.production_id) for e in received}
        assert str(pid1) in pids
        assert str(pid2) in pids
