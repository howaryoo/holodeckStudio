from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_type: str = Field(description="Event type identifier")
    production_id: UUID = Field(description="Production this event belongs to")
    episode_id: UUID | None = Field(default=None, description="Episode this event belongs to")
    stage_id: UUID | None = Field(default=None, description="Stage this event belongs to")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID = Field(default_factory=uuid4, description="Links related events")


# --- Production lifecycle events ---


class ProductionStarted(BaseEvent):
    event_type: Literal["production.started"] = "production.started"
    theme_prompt: str
    mode: Literal["autonomous", "supervised"]
    config: dict


class ProductionPaused(BaseEvent):
    event_type: Literal["production.paused"] = "production.paused"
    reason: str


class ProductionResumed(BaseEvent):
    event_type: Literal["production.resumed"] = "production.resumed"


class ProductionCompleted(BaseEvent):
    event_type: Literal["production.completed"] = "production.completed"
    output_path: str
    total_cost_usd: Decimal = Decimal("0")
    total_duration_seconds: float = 0.0


class ProductionFailed(BaseEvent):
    event_type: Literal["production.failed"] = "production.failed"
    error_stage: str
    error_agent: str
    error_message: str
    recoverable: bool = False


# --- Stage lifecycle events ---


class StageStarted(BaseEvent):
    event_type: Literal["stage.started"] = "stage.started"
    stage_type: str
    agent_role: str
    iteration: int = 0


class StageCompleted(BaseEvent):
    event_type: Literal["stage.completed"] = "stage.completed"
    stage_type: str
    agent_role: str
    output_assets: list[UUID] = []
    quality_score: int = Field(default=0, ge=0, le=100)


class StageAwaitingApproval(BaseEvent):
    event_type: Literal["stage.awaiting_approval"] = "stage.awaiting_approval"
    stage_type: str
    checkpoint_id: UUID = Field(default_factory=uuid4)
    timeout_at: datetime | None = None


class StageApproved(BaseEvent):
    event_type: Literal["stage.approved"] = "stage.approved"
    stage_type: str
    checkpoint_id: UUID
    reviewer: str
    note: str | None = None


class StageRejected(BaseEvent):
    event_type: Literal["stage.rejected"] = "stage.rejected"
    stage_type: str
    checkpoint_id: UUID
    reviewer: str
    feedback: str


class StageIterationExceeded(BaseEvent):
    event_type: Literal["stage.iteration_exceeded"] = "stage.iteration_exceeded"
    stage_type: str
    iteration_count: int
    max_iterations: int


# --- Agent communication events ---


class RevisionRequested(BaseEvent):
    event_type: Literal["agent.revision_requested"] = "agent.revision_requested"
    requesting_agent: str
    target_agent: str
    target_stage: str
    feedback: str


class ConflictDetected(BaseEvent):
    event_type: Literal["agent.conflict_detected"] = "agent.conflict_detected"
    agent_a: str
    agent_b: str
    conflict_description: str
    conflict_count: int = 1


class ConflictResolved(BaseEvent):
    event_type: Literal["agent.conflict_resolved"] = "agent.conflict_resolved"
    resolving_authority: Literal["showrunner", "human"]
    resolution: str
    escalation_threshold_reached: bool = False


class PromptRejected(BaseEvent):
    event_type: Literal["prompt.rejected"] = "prompt.rejected"
    original_prompt: str
    rejection_reason: Literal["too_vague", "too_short", "missing_genre", "missing_theme"]
    guidance: str


# --- Review events ---


class ReviewCompleted(BaseEvent):
    event_type: Literal["review.completed"] = "review.completed"
    reviewer_type: Literal["critic", "audience_simulation", "qa"]
    narrative_score: int = Field(default=0, ge=0, le=100)
    consistency_score: int = Field(default=0, ge=0, le=100)
    pacing_score: int = Field(default=0, ge=0, le=100)
    overall_score: int = Field(default=0, ge=0, le=100)
    passed: bool = False


class QualityGateFailed(BaseEvent):
    event_type: Literal["review.quality_gate_failed"] = "review.quality_gate_failed"
    stage_type: str
    overall_score: int
    threshold: int
    review_ids: list[UUID] = []


# --- Event bus protocol ---


from typing import Protocol


class EventBus(Protocol):
    async def publish(self, event: BaseEvent) -> None:
        ...

    async def subscribe(
        self,
        event_types: list[str],
        production_id: UUID | None = None,
    ) -> AsyncIterator[BaseEvent]:
        ...


import asyncio
from collections import defaultdict


import uuid

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


class RedisEventBus:
    STREAM_PREFIX = "holodeck:events"

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        consumer_group: str = "holodeck-pipeline",
        consumer_name: str | None = None,
        maxlen: int = 10000,
    ) -> None:
        if aioredis is None:
            raise ImportError("redis package required for RedisEventBus")
        self._redis_url = redis_url
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name or f"consumer-{uuid.uuid4().hex[:8]}"
        self._maxlen = maxlen
        self._redis: aioredis.Redis | None = None
        self._streams: dict[str, str] = {}
        self._running = False

    def _stream_key(self, event_type: str) -> str:
        return f"{self.STREAM_PREFIX}:{event_type}"

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def _ensure_group(self, stream_key: str) -> None:
        r = await self._get_redis()
        try:
            await r.xgroup_create(stream_key, self._consumer_group, id="$", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def publish(self, event: BaseEvent) -> None:
        stream_key = self._stream_key(event.event_type)
        r = await self._get_redis()
        await self._ensure_group(stream_key)
        data = event.model_dump(mode="json")
        data["_event_type"] = event.event_type
        data["_production_id"] = str(event.production_id) if event.production_id else ""
        data["_timestamp"] = event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp)
        await r.xadd(stream_key, data, maxlen=self._maxlen)

    async def subscribe(
        self,
        event_types: list[str],
        production_id: UUID | None = None,
    ) -> AsyncIterator[BaseEvent]:
        self._running = True
        r = await self._get_redis()
        stream_keys = [self._stream_key(et) for et in event_types]
        for sk in stream_keys:
            await self._ensure_group(sk)

        id_map = {sk: ">" for sk in stream_keys}
        while self._running:
            try:
                results = await r.xreadgroup(
                    groupname=self._consumer_group,
                    consumername=self._consumer_name,
                    streams=id_map,
                    count=10,
                    block=1000,
                )
                if not results:
                    continue
                for stream_key, messages in results:
                    for msg_id, msg_data in messages:
                        event_type = msg_data.get("_event_type", stream_key.split(":")[-1])
                        event_prod_id = msg_data.get("_production_id", "")
                        if production_id and event_prod_id and event_prod_id != str(production_id):
                            continue
                        event_data = {k: v for k, v in msg_data.items() if not k.startswith("_")}
                        event_data["event_type"] = event_type
                        if production_id:
                            event_data["production_id"] = production_id
                        if "production_id" in event_data and isinstance(event_data["production_id"], str):
                            try:
                                event_data["production_id"] = uuid.UUID(event_data["production_id"])
                            except (ValueError, AttributeError):
                                pass
                        event_cls = _EVENT_TYPE_MAP.get(event_type, BaseEvent)
                        try:
                            event = event_cls(**event_data)
                        except Exception:
                            event = BaseEvent(**{k: v for k, v in event_data.items() if k in BaseEvent.model_fields})
                        yield event
                        await r.xack(stream_key, self._consumer_group, msg_id)
            except aioredis.ConnectionError:
                if self._running:
                    await asyncio.sleep(1)
                continue

    async def close(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.close()
            self._redis = None


_EVENT_TYPE_MAP: dict[str, type[BaseEvent]] = {
    "production.started": ProductionStarted,
    "production.paused": ProductionPaused,
    "production.resumed": ProductionResumed,
    "production.completed": ProductionCompleted,
    "production.failed": ProductionFailed,
    "stage.started": StageStarted,
    "stage.completed": StageCompleted,
    "stage.awaiting_approval": StageAwaitingApproval,
    "stage.approved": StageApproved,
    "stage.rejected": StageRejected,
    "stage.iteration_exceeded": StageIterationExceeded,
    "agent.revision_requested": RevisionRequested,
    "agent.conflict_detected": ConflictDetected,
    "agent.conflict_resolved": ConflictResolved,
    "prompt.rejected": PromptRejected,
    "review.completed": ReviewCompleted,
    "review.quality_gate_failed": QualityGateFailed,
}


class AsyncioEventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[BaseEvent]]] = defaultdict(list)
        self._production_queues: dict[UUID, list[asyncio.Queue[BaseEvent]]] = defaultdict(list)

    async def publish(self, event: BaseEvent) -> None:
        for queue in self._queues.get(event.event_type, []):
            await queue.put(event)
        if event.production_id:
            for queue in self._production_queues.get(event.production_id, []):
                await queue.put(event)

    async def subscribe(
        self,
        event_types: list[str],
        production_id: UUID | None = None,
    ) -> AsyncIterator[BaseEvent]:
        queue: asyncio.Queue[BaseEvent] = asyncio.Queue()
        for event_type in event_types:
            self._queues[event_type].append(queue)
        if production_id:
            self._production_queues[production_id].append(queue)
        while True:
            event = await queue.get()
            yield event