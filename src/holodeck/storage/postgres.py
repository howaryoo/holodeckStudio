from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from holodeck.pipeline.stages import (
    AgentRole,
    CheckpointStatus,
    CheckpointType,
    ProductionMode,
    ProductionStatus,
    StageStatus,
    StageType,
)


class Base(DeclarativeBase):
    pass


class Production(Base):
    __tablename__ = "productions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    theme_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ProductionStatus] = mapped_column(
        SAEnum(ProductionStatus), nullable=False, default=ProductionStatus.PENDING
    )
    mode: Mapped[ProductionMode] = mapped_column(
        SAEnum(ProductionMode), nullable=False, default=ProductionMode.AUTONOMOUS
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    config_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("production_configs.id"), nullable=True
    )

    config: Mapped[ProductionConfig | None] = relationship("ProductionConfig")
    episodes: Mapped[list[Episode]] = relationship(back_populates="production")


class ProductionConfig(Base):
    __tablename__ = "production_configs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    max_feedback_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    conflict_escalation_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    quality_gate_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    human_approval_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    model_overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class FranchiseBible(Base):
    __tablename__ = "franchise_bibles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    entries: Mapped[list[BibleEntry]] = relationship(back_populates="bible")


class BibleEntry(Base):
    __tablename__ = "bible_entries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bible_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("franchise_bibles.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    bible: Mapped[FranchiseBible] = relationship(back_populates="entries")


class ActorVoiceSample(Base):
    __tablename__ = "actor_voice_samples"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bible_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("franchise_bibles.id"), nullable=False
    )
    character_name: Mapped[str] = mapped_column(String, nullable=False)
    sample_file_path: Mapped[str] = mapped_column(String, nullable=False)
    source_format: Mapped[str] = mapped_column(String, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(nullable=False)
    elevenlabs_voice_id: Mapped[str | None] = mapped_column(String, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    bible: Mapped[FranchiseBible] = relationship("FranchiseBible")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    production_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("productions.id"), nullable=False
    )
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(SAEnum(StageType), nullable=False, default=StageType.CONCEPT.value)
    current_stage: Mapped[str] = mapped_column(
        SAEnum(StageType), nullable=False, default=StageType.CONCEPT.value
    )
    feedback_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    production: Mapped[Production] = relationship(back_populates="episodes")
    stages: Mapped[list[Stage]] = relationship(back_populates="episode")


class Stage(Base):
    __tablename__ = "stages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id"), nullable=False
    )
    stage_type: Mapped[StageType] = mapped_column(SAEnum(StageType), nullable=False)
    status: Mapped[StageStatus] = mapped_column(
        SAEnum(StageStatus), nullable=False, default=StageStatus.PENDING
    )
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    episode: Mapped[Episode] = relationship(back_populates="stages")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id"), nullable=False
    )
    stage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stages.id"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(
        SAEnum(
            "script",
            "storyboard",
            "character_sheet",
            "environment_design",
            "music",
            "sound_effect",
            "voice_performance",
            "animation_frame",
            "rendered_video",
            "review_report",
            name="asset_type",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    episode_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id"), nullable=False
    )
    stage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stages.id"), nullable=False
    )
    reviewer_type: Mapped[str] = mapped_column(
        SAEnum("critic", "audience_simulation", "qa", name="reviewer_type"), nullable=False
    )
    narrative_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consistency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pacing_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ApprovalCheckpoint(Base):
    __tablename__ = "approval_checkpoints"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    stage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stages.id"), nullable=False
    )
    checkpoint_type: Mapped[CheckpointType] = mapped_column(SAEnum(CheckpointType), nullable=False)
    status: Mapped[CheckpointStatus] = mapped_column(
        SAEnum(CheckpointStatus), nullable=False, default=CheckpointStatus.PENDING
    )
    reviewer: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timeout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    production_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("productions.id"), nullable=False
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("episodes.id"), nullable=True
    )
    stage_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("stages.id"), nullable=True
    )
    agent_role: Mapped[AgentRole] = mapped_column(SAEnum(AgentRole), nullable=False)
    langfuse_trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    status: Mapped[str] = mapped_column(SAEnum("running", "completed", "failed", name="execution_status"), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# --- Async session factory ---

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from holodeck.config.settings import Settings

_engine = None
_session_factory = None
_engine_loop_id = None


def init_db(database_url: str | None = None) -> None:
    global _engine, _session_factory, _engine_loop_id
    try:
        import asyncio
        _engine_loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        _engine_loop_id = None
    url = database_url or Settings().database_url
    _engine = create_async_engine(url, echo=False, pool_size=5, max_overflow=10)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def get_engine():
    if _engine is None:
        init_db()
    return _engine


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    global _engine, _session_factory, _engine_loop_id
    try:
        import asyncio
        current_loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        current_loop_id = None
    if _session_factory is None or (_engine_loop_id is not None and current_loop_id != _engine_loop_id):
        init_db()
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# --- CRUD Repositories ---


class ProductionRepository:
    async def create(self, production: Production) -> Production:
        async with get_session() as session:
            session.add(production)
            return production

    async def get(self, production_id: UUID) -> Production | None:
        async with get_session() as session:
            return await session.get(Production, production_id)

    async def update(self, production: Production) -> Production:
        async with get_session() as session:
            session.add(production)
            return production

    async def list(self) -> list[Production]:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Production).order_by(Production.created_at.desc()))
            return list(result.scalars().all())


class BibleRepository:
    async def create(self, bible: FranchiseBible) -> FranchiseBible:
        async with get_session() as session:
            session.add(bible)
            return bible

    async def get(self, bible_id: UUID) -> FranchiseBible | None:
        async with get_session() as session:
            return await session.get(FranchiseBible, bible_id)

    async def list(self) -> list[FranchiseBible]:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(FranchiseBible).order_by(FranchiseBible.name))
            return list(result.scalars().all())

    async def add_entry(self, entry: BibleEntry) -> BibleEntry:
        async with get_session() as session:
            session.add(entry)
            return entry

    async def delete_entries(self, bible_id: UUID) -> None:
        async with get_session() as session:
            from sqlalchemy import delete
            await session.execute(delete(BibleEntry).where(BibleEntry.bible_id == bible_id))

    async def search_entries(self, bible_id: UUID, query: str) -> list[BibleEntry]:
        async with get_session() as session:
            from sqlalchemy import select
            stmt = select(BibleEntry).where(
                BibleEntry.bible_id == bible_id,
                BibleEntry.content.ilike(f"%{query}%"),
            ).limit(20)
            result = await session.execute(stmt)
            return list(result.scalars().all())


class EpisodeRepository:
    async def create(self, episode: Episode) -> Episode:
        async with get_session() as session:
            session.add(episode)
            return episode

    async def get(self, episode_id: UUID) -> Episode | None:
        async with get_session() as session:
            return await session.get(Episode, episode_id)

    async def update(self, episode: Episode) -> Episode:
        async with get_session() as session:
            session.add(episode)
            return episode


class StageRepository:
    async def create(self, stage: Stage) -> Stage:
        async with get_session() as session:
            session.add(stage)
            return stage

    async def get(self, stage_id: UUID) -> Stage | None:
        async with get_session() as session:
            return await session.get(Stage, stage_id)

    async def update(self, stage: Stage) -> Stage:
        async with get_session() as session:
            session.add(stage)
            return stage

    async def list_by_episode(self, episode_id: UUID) -> list[Stage]:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Stage).where(Stage.episode_id == episode_id).order_by(Stage.started_at)
            )
            return list(result.scalars().all())


class ReviewRepository:
    async def create(self, review: Review) -> Review:
        async with get_session() as session:
            session.add(review)
            return review

    async def list_by_episode(self, episode_id: UUID) -> list[Review]:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Review).where(Review.episode_id == episode_id)
            )
            return list(result.scalars().all())


class AgentExecutionRepository:
    async def create(self, execution: AgentExecution) -> AgentExecution:
        async with get_session() as session:
            session.add(execution)
            return execution

    async def list_by_production(self, production_id: UUID) -> list[AgentExecution]:
        async with get_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AgentExecution).where(AgentExecution.production_id == production_id)
            )
            return list(result.scalars().all())


class ActorVoiceSampleRepository:
    async def create(self, sample: ActorVoiceSample) -> ActorVoiceSample:
        async with get_session() as session:
            session.add(sample)
            return sample

    async def get_active(self, bible_id: UUID, character_name: str) -> ActorVoiceSample | None:
        from sqlalchemy import func, or_, select
        # "RACHEL" → "rachel", "Rachel Green" → "rachel green"
        name_lower = character_name.lower().strip()
        # First word: "rachel" from "RACHEL" or "RACHEL GREEN"
        first_word = name_lower.split()[0] if name_lower.split() else name_lower
        async with get_session() as session:
            result = await session.execute(
                select(ActorVoiceSample).where(
                    ActorVoiceSample.bible_id == bible_id,
                    ActorVoiceSample.is_active.is_(True),
                    or_(
                        # Exact: "Rachel Green" == "rachel green"
                        func.lower(ActorVoiceSample.character_name) == name_lower,
                        # Stored starts with first word: "rachel green" LIKE "rachel%"
                        func.lower(ActorVoiceSample.character_name).like(first_word + "%"),
                    ),
                )
            )
            rows = list(result.scalars().all())
            if not rows:
                return None
            # Prefer exact match over prefix match
            exact = [r for r in rows if r.character_name.lower() == name_lower]
            return exact[0] if exact else rows[0]

    async def list_by_bible(self, bible_id: UUID) -> list[ActorVoiceSample]:
        from sqlalchemy import select
        async with get_session() as session:
            result = await session.execute(
                select(ActorVoiceSample)
                .where(ActorVoiceSample.bible_id == bible_id)
                .order_by(ActorVoiceSample.character_name)
            )
            return list(result.scalars().all())

    async def update_voice_id(self, sample_id: UUID, voice_id: str) -> None:
        from sqlalchemy import update
        async with get_session() as session:
            await session.execute(
                update(ActorVoiceSample)
                .where(ActorVoiceSample.id == sample_id)
                .values(elevenlabs_voice_id=voice_id)
            )

    async def deactivate(self, bible_id: UUID, character_name: str) -> None:
        from sqlalchemy import func, update
        async with get_session() as session:
            await session.execute(
                update(ActorVoiceSample)
                .where(
                    ActorVoiceSample.bible_id == bible_id,
                    func.lower(ActorVoiceSample.character_name) == character_name.lower(),
                    ActorVoiceSample.is_active.is_(True),
                )
                .values(is_active=False)
            )
