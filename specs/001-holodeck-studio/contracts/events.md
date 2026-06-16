# Event Schemas Contract: Holodeck Studio

**Feature**: 001-holodeck-studio
**Date**: 2026-06-07

This document defines the internal event types used for inter-agent communication via the event bus. All events are Pydantic models serialized as JSON.

## Base Event

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from enum import Enum

class BaseEvent(BaseModel):
    event_type: str = Field(description="Event type identifier")
    production_id: UUID = Field(description="Production this event belongs to")
    episode_id: UUID | None = Field(default=None, description="Episode this event belongs to")
    stage_id: UUID | None = Field(default=None, description="Stage this event belongs to")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID = Field(description="Links related events across the pipeline")
```

## Production Lifecycle Events

### ProductionStarted
```python
class ProductionStarted(BaseEvent):
    event_type: Literal["production.started"] = "production.started"
    theme_prompt: str
    mode: Literal["autonomous", "supervised"]
    config: ProductionConfigSnapshot
```

### ProductionPaused
```python
class ProductionPaused(BaseEvent):
    event_type: Literal["production.paused"] = "production.paused"
    reason: str
```

### ProductionResumed
```python
class ProductionResumed(BaseEvent):
    event_type: Literal["production.resumed"] = "production.resumed"
```

### ProductionCompleted
```python
class ProductionCompleted(BaseEvent):
    event_type: Literal["production.completed"] = "production.completed"
    output_path: str
    total_cost_usd: Decimal
    total_duration_seconds: float
```

### ProductionFailed
```python
class ProductionFailed(BaseEvent):
    event_type: Literal["production.failed"] = "production.failed"
    error_stage: StageType
    error_agent: AgentRole
    error_message: str
    recoverable: bool
```

## Stage Lifecycle Events

### StageStarted
```python
class StageStarted(BaseEvent):
    event_type: Literal["stage.started"] = "stage.started"
    stage_type: StageType
    agent_role: AgentRole
    iteration: int
```

### StageCompleted
```python
class StageCompleted(BaseEvent):
    event_type: Literal["stage.completed"] = "stage.completed"
    stage_type: StageType
    agent_role: AgentRole
    output_assets: list[UUID]
    quality_score: int = Field(ge=0, le=100)
```

### StageAwaitingApproval
```python
class StageAwaitingApproval(BaseEvent):
    event_type: Literal["stage.awaiting_approval"] = "stage.awaiting_approval"
    stage_type: StageType
    checkpoint_id: UUID
    timeout_at: datetime | None
```

### StageApproved
```python
class StageApproved(BaseEvent):
    event_type: Literal["stage.approved"] = "stage.approved"
    stage_type: StageType
    checkpoint_id: UUID
    reviewer: str
    note: str | None
```

### StageRejected
```python
class StageRejected(BaseEvent):
    event_type: Literal["stage.rejected"] = "stage.rejected"
    stage_type: StageType
    checkpoint_id: UUID
    reviewer: str
    feedback: str
```

### StageIterationExceeded
```python
class StageIterationExceeded(BaseEvent):
    event_type: Literal["stage.iteration_exceeded"] = "stage.iteration_exceeded"
    stage_type: StageType
    iteration_count: int
    max_iterations: int
```

## Agent Communication Events

### RevisionRequested
```python
class RevisionRequested(BaseEvent):
    event_type: Literal["agent.revision_requested"] = "agent.revision_requested"
    requesting_agent: AgentRole
    target_agent: AgentRole
    target_stage: StageType
    feedback: str
```

### ConflictDetected
```python
class ConflictDetected(BaseEvent):
    event_type: Literal["agent.conflict_detected"] = "agent.conflict_detected"
    agent_a: AgentRole
    agent_b: AgentRole
    conflict_description: str
    conflict_count: int = Field(description="Running count of conflicts for escalation")
```

### ConflictResolved
```python
class ConflictResolved(BaseEvent):
    event_type: Literal["agent.conflict_resolved"] = "agent.conflict_resolved"
    resolving_authority: Literal["showrunner", "human"]
    resolution: str
    escalation_threshold_reached: bool
```

### PromptRejected
```python
class PromptRejected(BaseEvent):
    event_type: Literal["prompt.rejected"] = "prompt.rejected"
    original_prompt: str
    rejection_reason: Literal["too_vague", "too_short", "missing_genre", "missing_theme"]
    guidance: str
```

## Review Events

### ReviewCompleted
```python
class ReviewCompleted(BaseEvent):
    event_type: Literal["review.completed"] = "review.completed"
    reviewer_type: Literal["critic", "audience_simulation", "qa"]
    narrative_score: int = Field(ge=0, le=100)
    consistency_score: int = Field(ge=0, le=100)
    pacing_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    passed: bool
```

### QualityGateFailed
```python
class QualityGateFailed(BaseEvent):
    event_type: Literal["review.quality_gate_failed"] = "review.quality_gate_failed"
    stage_type: StageType
    overall_score: int
    threshold: int
    review_ids: list[UUID]
```

## Event Bus Interface

```python
from typing import Protocol, AsyncIterator
from uuid import UUID

class EventBus(Protocol):
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all subscribers."""
        ...

    async def subscribe(
        self,
        event_types: list[str],
        production_id: UUID | None = None,
    ) -> AsyncIterator[BaseEvent]:
        """Subscribe to events matching the given types and optional production filter."""
        ...
```

Two implementations:
- `AsyncioEventBus`: Single-process, uses `asyncio.Queue` for local development
- `RedisEventBus`: Multi-process, uses Redis Streams for cloud deployment