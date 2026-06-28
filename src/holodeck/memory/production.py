from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from holodeck.pipeline.stages import ProductionStatus, ProductionMode

try:
    from holodeck.storage.postgres import (
        ProductionRepository,
        EpisodeRepository,
        AgentExecutionRepository,
    )
    _HAS_DB = True
except Exception:
    _HAS_DB = False

_PRODUCTION_REGISTRY: dict[str, ProductionMemory] = {}


def register_production(memory: ProductionMemory) -> None:
    _PRODUCTION_REGISTRY[str(memory.id)] = memory


def get_production(production_id: str) -> ProductionMemory | None:
    mem = _PRODUCTION_REGISTRY.get(production_id)
    if mem is not None:
        return mem
    if _HAS_DB:
        try:
            import asyncio
            uid = UUID(production_id)
            return asyncio.run(ProductionMemory.from_db(uid))
        except Exception:
            pass
    return None


def list_productions() -> list[dict[str, Any]]:
    result = [p.to_dict() for p in _PRODUCTION_REGISTRY.values()]
    if _HAS_DB:
        try:
            import asyncio
            from holodeck.storage.postgres import ProductionRepository
            repo = ProductionRepository()
            db_prods = asyncio.run(repo.list())
            for dbp in db_prods:
                pid = str(dbp.id)
                if pid not in _PRODUCTION_REGISTRY:
                    result.append({
                        "id": pid,
                        "status": dbp.status.value if hasattr(dbp.status, 'value') else str(dbp.status),
                        "mode": dbp.mode.value if hasattr(dbp.mode, 'value') else str(dbp.mode),
                        "theme_prompt": dbp.theme_prompt,
                        "created_at": str(dbp.created_at),
                    })
        except Exception:
            pass
    return result


class ProductionMemory:
    def __init__(self, production_id: UUID | None = None) -> None:
        self.id = production_id or uuid4()
        self._status: ProductionStatus = ProductionStatus.PENDING
        self._mode: ProductionMode = ProductionMode.AUTONOMOUS
        self._theme_prompt: str = ""
        self._episodes: dict[UUID, dict[str, Any]] = {}
        self._episode_memories: dict[UUID, Any] = {}
        self._agent_executions: list[dict[str, Any]] = []
        self._approvals: list[dict[str, Any]] = []
        self._config: dict[str, Any] = {}

    @property
    def status(self) -> ProductionStatus:
        return self._status

    @status.setter
    def status(self, status: ProductionStatus) -> None:
        self._status = status

    @property
    def mode(self) -> ProductionMode:
        return self._mode

    @mode.setter
    def mode(self, mode: ProductionMode) -> None:
        self._mode = mode

    def set_theme_prompt(self, prompt: str) -> None:
        self._theme_prompt = prompt

    def get_theme_prompt(self) -> str:
        return self._theme_prompt

    def add_episode(self, episode_id: UUID, episode_data: dict[str, Any]) -> None:
        self._episodes[episode_id] = episode_data

    def register_episode_memory(self, episode_id: UUID, episode_memory: Any) -> None:
        self._episode_memories[episode_id] = episode_memory

    def get_episode_memory(self, episode_id: UUID) -> Any | None:
        return self._episode_memories.get(episode_id)

    def get_all_episode_memories(self) -> list[Any]:
        return list(self._episode_memories.values())

    def get_episode(self, episode_id: UUID) -> dict[str, Any] | None:
        return self._episodes.get(episode_id)

    def get_all_episodes(self) -> list[dict[str, Any]]:
        return list(self._episodes.values())

    def add_approval(self, approval: dict[str, Any]) -> None:
        self._approvals.append(approval)

    def get_approvals(self, stage: str | None = None) -> list[dict[str, Any]]:
        if stage:
            return [a for a in self._approvals if a.get("stage") == stage]
        return self._approvals

    def add_agent_execution(self, execution: dict[str, Any]) -> None:
        self._agent_executions.append(execution)

    def get_agent_executions(self, agent_role: str | None = None) -> list[dict[str, Any]]:
        if agent_role:
            return [e for e in self._agent_executions if e.get("agent_role") == agent_role]
        return self._agent_executions

    def set_config(self, config: dict[str, Any]) -> None:
        self._config = config

    def get_config(self) -> dict[str, Any]:
        return self._config

    def calculate_total_cost(self) -> float:
        return sum(e.get("cost_usd", 0) for e in self._agent_executions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "status": self._status.value,
            "mode": self._mode.value,
            "theme_prompt": self._theme_prompt,
            "episodes": {str(k): v for k, v in self._episodes.items()},
            "agent_executions": self._agent_executions,
            "approvals": self._approvals,
            "config": self._config,
            "total_cost_usd": self.calculate_total_cost(),
        }

    async def persist_to_db(self) -> None:
        if not _HAS_DB:
            return
        prod_repo = ProductionRepository()
        from holodeck.storage.postgres import Production as DBProduction
        db_prod = await prod_repo.get(self.id)
        if db_prod is None:
            db_prod = DBProduction(
                id=self.id,
                theme_prompt=self._theme_prompt,
                status=self._status,
                mode=self._mode,
            )
            await prod_repo.create(db_prod)
        else:
            db_prod.theme_prompt = self._theme_prompt
            db_prod.status = self._status
            db_prod.mode = self._mode
            await prod_repo.update(db_prod)
        ep_repo = EpisodeRepository()
        from holodeck.storage.postgres import Episode as DBEpisode
        for ep_id, ep_data in self._episodes.items():
            db_ep = await ep_repo.get(ep_id)
            if db_ep is None:
                db_ep = DBEpisode(
                    id=ep_id,
                    production_id=self.id,
                    episode_number=ep_data.get("episode_number", 0),
                    title=ep_data.get("title"),
                )
                await ep_repo.create(db_ep)
            else:
                await ep_repo.update(db_ep)
        exec_repo = AgentExecutionRepository()
        from holodeck.storage.postgres import AgentExecution as DBAgentExecution
        for ex in self._agent_executions:
            exec_id = ex.get("id")
            if exec_id and isinstance(exec_id, UUID):
                pass
            else:
                db_ex = DBAgentExecution(
                    production_id=self.id,
                    episode_id=ex.get("episode_id"),
                    stage_id=ex.get("stage_id"),
                    agent_role=ex.get("agent_role", "showrunner"),
                    langfuse_trace_id=ex.get("langfuse_trace_id"),
                    model_provider=ex.get("model_provider"),
                    model_id=ex.get("model_id"),
                    input_tokens=ex.get("input_tokens"),
                    output_tokens=ex.get("output_tokens"),
                    cost_usd=ex.get("cost_usd"),
                )
                await exec_repo.create(db_ex)

    @classmethod
    async def from_db(cls, production_id: UUID) -> ProductionMemory | None:
        if not _HAS_DB:
            return None
        prod_repo = ProductionRepository()
        db_prod = await prod_repo.get(production_id)
        if db_prod is None:
            return None
        mem = cls(production_id)
        mem._status = db_prod.status
        mem._mode = db_prod.mode
        mem._theme_prompt = db_prod.theme_prompt
        register_production(mem)
        from holodeck.storage.postgres import Episode as DBEpisode
        from sqlalchemy import select
        from holodeck.storage.postgres import get_session
        async with get_session() as session:
            result = await session.execute(
                select(DBEpisode).where(DBEpisode.production_id == production_id)
            )
            for db_ep in result.scalars().all():
                mem._episodes[db_ep.id] = {
                    "episode_number": db_ep.episode_number,
                    "title": db_ep.title,
                    "status": db_ep.status,
                }
        exec_repo = AgentExecutionRepository()
        db_execs = await exec_repo.list_by_production(production_id)
        for db_ex in db_execs:
            mem._agent_executions.append({
                "id": db_ex.id,
                "episode_id": db_ex.episode_id,
                "stage_id": db_ex.stage_id,
                "agent_role": db_ex.agent_role.value,
                "langfuse_trace_id": db_ex.langfuse_trace_id,
                "model_provider": db_ex.model_provider,
                "model_id": db_ex.model_id,
                "input_tokens": db_ex.input_tokens,
                "output_tokens": db_ex.output_tokens,
                "cost_usd": float(db_ex.cost_usd) if db_ex.cost_usd else 0.0,
            })
        return mem