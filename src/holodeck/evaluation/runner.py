from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from holodeck.evaluation.schemas import (
    REJECTION_THRESHOLD,
    BatchEvaluationReport,
    DimensionScore,
    EvaluationDimension,
    EvaluationFailure,
    EvaluationResult,
    GoldenDatasetEntry,
    GuidelineComparison,
)

if TYPE_CHECKING:
    from agno.models.base import Model

    from holodeck.config.settings import Settings

logger = logging.getLogger(__name__)


class EvaluationRunner:
    def __init__(self, model: Model | None = None, settings: Settings | None = None) -> None:
        from holodeck.agents.evaluation.judge import JudgeAgent
        from holodeck.config.registry import model_for_agent
        from holodeck.config.settings import Settings as _Settings

        self._settings = settings or _Settings()
        if model is None:
            model = model_for_agent("evaluator", self._settings)

        self._judge = JudgeAgent(model=model)

    def evaluate_single(
        self,
        entry: GoldenDatasetEntry,
        script_content: str = "",
        script_id: str | None = None,
        dry_run: bool = False,
    ) -> EvaluationResult:
        if dry_run:
            return self._make_stub_result(entry, script_id or "dry-run-stub")

        sid = script_id or f"script-{entry.prompt_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        context = {
            "content": script_content,
            "guidelines": entry.quality_guidelines.model_dump(),
        }

        agent_output = self._judge.process(context)
        raw_scores: list[dict] = agent_output.metadata.get("dimension_scores", [])
        dimension_scores = [DimensionScore(**s) for s in raw_scores]

        overall = sum(ds.weighted_score for ds in dimension_scores)
        passed = overall >= REJECTION_THRESHOLD

        red_flags = self._collect_red_flags(script_content, dimension_scores)
        comparison = self._compare_to_guidelines(script_content, entry, dimension_scores)

        previous_score, regression = self._check_regression(entry.prompt_id, overall)

        result = EvaluationResult(
            script_id=sid,
            golden_entry_id=entry.prompt_id,
            dimension_scores=dimension_scores,
            passed_quality_gate=passed,
            red_flags_triggered=red_flags,
            guideline_comparison=comparison,
            previous_score=previous_score,
            regression_detected=regression,
        )

        self._persist(result)
        return result

    def run_full(self, entry: GoldenDatasetEntry) -> EvaluationResult:
        """Run ProductionPipeline for entry.user_prompt, then evaluate the script."""
        import asyncio

        from holodeck.pipeline.runner import ProductionPipeline

        logger.info("run_full: running pipeline for '%s'", entry.prompt_id)
        pipeline = ProductionPipeline(settings=self._settings)
        pipeline_result = asyncio.run(pipeline.run(entry.user_prompt, script_only=True))

        script_content = pipeline_result.script
        logger.info("run_full: script ready (%d chars), evaluating", len(script_content))
        return self.evaluate_single(entry, script_content=script_content)

    def run_full_batch(self, entries: list[GoldenDatasetEntry]) -> BatchEvaluationReport:
        results: list[EvaluationResult] = []
        failures: list[EvaluationFailure] = []

        for entry in entries:
            try:
                results.append(self.run_full(entry))
            except Exception as exc:
                logger.warning("run_full failed for %s: %s", entry.prompt_id, exc)
                failures.append(
                    EvaluationFailure(
                        golden_entry_id=entry.prompt_id,
                        error_message=str(exc),
                        error_type=type(exc).__name__,
                    )
                )

        return BatchEvaluationReport(
            golden_dataset_version="1.0",
            evaluation_results=results,
            failures=failures,
        )

    def run_batch(self, entries: list[GoldenDatasetEntry], **kwargs: object) -> BatchEvaluationReport:
        results: list[EvaluationResult] = []
        failures: list[EvaluationFailure] = []

        for entry in entries:
            try:
                result = self.evaluate_single(entry, **kwargs)  # type: ignore[arg-type]
                results.append(result)
            except Exception as exc:
                error_type = type(exc).__name__
                logger.warning("Evaluation failed for %s: %s", entry.prompt_id, exc)
                failures.append(
                    EvaluationFailure(
                        golden_entry_id=entry.prompt_id,
                        error_message=str(exc),
                        error_type=error_type,
                    )
                )

        return BatchEvaluationReport(
            golden_dataset_version="1.0",
            evaluation_results=results,
            failures=failures,
        )

    def get_history(self, golden_entry_id: str) -> list[EvaluationResult]:
        try:
            import asyncio

            from holodeck.storage.postgres import EvaluationRepository

            return asyncio.run(EvaluationRepository().get_by_entry(golden_entry_id))
        except Exception as exc:
            logger.warning("Cannot retrieve history (DB unavailable?): %s", exc)
            return []

    def _check_regression(self, golden_entry_id: str, current_score: float) -> tuple[float | None, bool]:
        history = self.get_history(golden_entry_id)
        if not history:
            return None, False
        prior_score = history[0].overall_score()
        dropped = (prior_score - current_score) / prior_score > 0.10 if prior_score > 0 else False
        return prior_score, dropped

    def _collect_red_flags(self, script_content: str, dimension_scores: list[DimensionScore]) -> list[str]:
        triggered: list[str] = []
        content_lower = script_content.lower()
        for _dim_name, meta in EvaluationDimension.DIMENSIONS.items():
            for flag in meta["red_flags"]:
                flag_lower = flag.lower()
                if any(keyword in content_lower for keyword in flag_lower.split()[:3]):
                    triggered.append(flag)
        return triggered

    def _compare_to_guidelines(
        self,
        script_content: str,
        entry: GoldenDatasetEntry,
        dimension_scores: list[DimensionScore],
    ) -> GuidelineComparison:
        content_lower = script_content.lower()
        met: list[str] = []
        partially_met: list[str] = []
        missed: list[str] = []

        all_requirements = (
            entry.scope_boundaries.must_include
            + entry.quality_guidelines.emotional_beats
            + list(entry.quality_guidelines.character_arcs.keys())
        )

        for req in all_requirements:
            keywords = [w.lower() for w in req.split() if len(w) > 3]
            matches = sum(1 for kw in keywords if kw in content_lower)
            if not keywords or matches >= len(keywords) * 0.7:
                met.append(req)
            elif matches > 0:
                partially_met.append(req)
            else:
                missed.append(req)

        variation_used: str | None = None
        for variation in entry.acceptable_variations:
            kws = [w.lower() for w in variation.split() if len(w) > 4]
            if kws and sum(1 for k in kws if k in content_lower) >= len(kws) * 0.5:
                variation_used = variation
                break

        return GuidelineComparison(
            met=met,
            partially_met=partially_met,
            missed=missed,
            variation_used=variation_used,
        )

    def _persist(self, result: EvaluationResult) -> None:
        try:
            import asyncio

            from holodeck.storage.postgres import EvaluationRepository
            asyncio.run(EvaluationRepository().save(result))
        except Exception as exc:
            logger.warning("Could not persist evaluation result (DB unavailable?): %s", exc)

    @staticmethod
    def _make_stub_result(entry: GoldenDatasetEntry, script_id: str) -> EvaluationResult:
        scores = [
            DimensionScore(
                dimension=dim,
                score=0.0,
                weight=meta["weight"],
                reasoning="dry-run stub",
                evidence=[],
            )
            for dim, meta in EvaluationDimension.DIMENSIONS.items()
        ]
        return EvaluationResult(
            script_id=script_id,
            golden_entry_id=entry.prompt_id,
            dimension_scores=scores,
            passed_quality_gate=False,
        )
