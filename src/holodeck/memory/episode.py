from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from holodeck.pipeline.stages import StageType

try:
    from holodeck.storage.postgres import (
        StageRepository,
        ReviewRepository,
        EpisodeRepository,
    )
    _HAS_DB = True
except Exception:
    _HAS_DB = False


class EpisodeMemory:
    def __init__(self, episode_id: UUID | None = None) -> None:
        self.id = episode_id or uuid4()
        self._stage_data: dict[str, dict[str, Any]] = {}
        self._current_stage: StageType = StageType.CONCEPT
        self._feedback_iterations: dict[str, int] = {}
        self._assets: dict[str, list[dict[str, Any]]] = {}
        self._reviews: list[dict[str, Any]] = []

    def set_stage_data(self, stage: StageType, data: dict[str, Any]) -> None:
        self._stage_data[stage.value] = data

    def get_stage_data(self, stage: StageType) -> dict[str, Any] | None:
        return self._stage_data.get(stage.value)

    @property
    def current_stage(self) -> StageType:
        return self._current_stage

    @current_stage.setter
    def current_stage(self, stage: StageType) -> None:
        self._current_stage = stage

    def increment_feedback_iteration(self, stage: StageType) -> int:
        key = stage.value
        current = self._feedback_iterations.get(key, 0)
        self._feedback_iterations[key] = current + 1
        return self._feedback_iterations[key]

    def get_feedback_iterations(self, stage: StageType) -> int:
        return self._feedback_iterations.get(stage.value, 0)

    def add_asset(self, stage: StageType, asset: dict[str, Any]) -> None:
        key = stage.value
        if key not in self._assets:
            self._assets[key] = []
        self._assets[key].append(asset)

    def get_assets(self, stage: StageType | None = None) -> list[dict[str, Any]]:
        if stage:
            return self._assets.get(stage.value, [])
        all_assets: list[dict[str, Any]] = []
        for stage_assets in self._assets.values():
            all_assets.extend(stage_assets)
        return all_assets

    def add_review(self, review: dict[str, Any]) -> None:
        self._reviews.append(review)

    def get_reviews(self, reviewer_type: str | None = None) -> list[dict[str, Any]]:
        if reviewer_type:
            return [r for r in self._reviews if r.get("reviewer_type") == reviewer_type]
        return self._reviews

    async def persist_to_db(self, production_id: UUID) -> None:
        if not _HAS_DB:
            return
        ep_repo = EpisodeRepository()
        from holodeck.storage.postgres import Episode as DBEpisode
        db_ep = await ep_repo.get(self.id)
        if db_ep is None:
            db_ep = DBEpisode(
                id=self.id,
                production_id=production_id,
                episode_number=1,
                status=self._current_stage.value,
                current_stage=self._current_stage.value,
            )
            await ep_repo.create(db_ep)
        stage_repo = StageRepository()
        from holodeck.storage.postgres import Stage as DBStage
        for stage_val, data in self._stage_data.items():
            stage_id = uuid4()
            db_stage = DBStage(
                id=stage_id,
                episode_id=self.id,
                stage_type=stage_val,
                output_data=data,
            )
            await stage_repo.create(db_stage)
        review_repo = ReviewRepository()
        from holodeck.storage.postgres import Review as DBReview
        for rv in self._reviews:
            db_rv = DBReview(
                id=uuid4(),
                episode_id=self.id,
                stage_id=uuid4(),
                reviewer_type=rv.get("reviewer", "critic"),
                content=rv.get("critique") or rv.get("report") or rv.get("content"),
            )
            await review_repo.create(db_rv)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "current_stage": self._current_stage.value,
            "stage_data": self._stage_data,
            "feedback_iterations": self._feedback_iterations,
            "assets": {k: v for k, v in self._assets.items()},
            "reviews": self._reviews,
        }