from __future__ import annotations

import pytest
from pydantic import ValidationError

from holodeck.evaluation.schemas import (
    REJECTION_THRESHOLD,
    BatchEvaluationReport,
    DimensionScore,
    EvaluationDimension,
    EvaluationResult,
    GoldenDatasetEntry,
    GuidelineComparison,
    QualityGuidelines,
    ScopeBoundaries,
)


def make_dimension_score(dimension: str, score: float = 0.8) -> DimensionScore:
    weight = EvaluationDimension.DIMENSIONS[dimension]["weight"]
    return DimensionScore(dimension=dimension, score=score, weight=weight)


def make_all_dimension_scores(score: float = 0.8) -> list[DimensionScore]:
    return [make_dimension_score(dim, score) for dim in EvaluationDimension.DIMENSIONS]


def make_evaluation_result(score: float = 0.8) -> EvaluationResult:
    scores = make_all_dimension_scores(score)
    overall = sum(ds.weighted_score for ds in scores)
    return EvaluationResult(
        script_id="test-script-001",
        golden_entry_id="rival-chef-s01",
        dimension_scores=scores,
        passed_quality_gate=overall >= REJECTION_THRESHOLD,
    )


class TestDimensionWeights:
    def test_weights_sum_to_one(self) -> None:
        total = EvaluationDimension.weight_sum()
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_exactly_eight_dimensions(self) -> None:
        assert len(EvaluationDimension.DIMENSIONS) == 8

    def test_dimension_names(self) -> None:
        expected = {
            "narrative_coherence",
            "character_consistency",
            "comedy_effectiveness",
            "dialogue_naturalness",
            "story_structure",
            "emotional_impact",
            "production_feasibility",
            "thematic_alignment",
        }
        assert set(EvaluationDimension.DIMENSIONS.keys()) == expected

    def test_each_dimension_has_required_keys(self) -> None:
        for name, dim in EvaluationDimension.DIMENSIONS.items():
            assert "description" in dim, f"{name} missing description"
            assert "weight" in dim, f"{name} missing weight"
            assert "signals" in dim, f"{name} missing signals"
            assert "red_flags" in dim, f"{name} missing red_flags"
            assert isinstance(dim["signals"], list) and len(dim["signals"]) > 0
            assert isinstance(dim["red_flags"], list) and len(dim["red_flags"]) > 0

    def test_character_consistency_is_highest_weight(self) -> None:
        weights = {k: v["weight"] for k, v in EvaluationDimension.DIMENSIONS.items()}
        assert weights["character_consistency"] == max(weights.values())

    def test_thematic_alignment_is_lowest_weight(self) -> None:
        weights = {k: v["weight"] for k, v in EvaluationDimension.DIMENSIONS.items()}
        assert weights["thematic_alignment"] == min(weights.values())


class TestDimensionScore:
    def test_weighted_score_is_score_times_weight(self) -> None:
        ds = DimensionScore(dimension="narrative_coherence", score=0.8, weight=0.15)
        assert abs(ds.weighted_score - 0.12) < 1e-9

    def test_score_zero_gives_zero_weighted(self) -> None:
        ds = DimensionScore(dimension="narrative_coherence", score=0.0, weight=0.15)
        assert ds.weighted_score == 0.0

    def test_score_one_gives_weight_as_weighted(self) -> None:
        ds = DimensionScore(dimension="narrative_coherence", score=1.0, weight=0.15)
        assert abs(ds.weighted_score - 0.15) < 1e-9

    def test_score_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore(dimension="x", score=-0.1, weight=0.5)

    def test_score_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore(dimension="x", score=1.1, weight=0.5)

    def test_weight_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore(dimension="x", score=0.5, weight=-0.1)

    def test_weight_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DimensionScore(dimension="x", score=0.5, weight=1.1)


class TestEvaluationResult:
    def test_overall_score_is_weighted_sum(self) -> None:
        result = make_evaluation_result(score=0.8)
        expected = sum(ds.weighted_score for ds in result.dimension_scores)
        assert abs(result.overall_score() - expected) < 1e-9

    def test_passed_quality_gate_above_threshold(self) -> None:
        result = make_evaluation_result(score=0.8)
        assert result.passed_quality_gate is True

    def test_failed_quality_gate_below_threshold(self) -> None:
        result = make_evaluation_result(score=0.2)
        assert result.passed_quality_gate is False

    def test_rejection_threshold_value(self) -> None:
        assert REJECTION_THRESHOLD == 0.35

    def test_regression_not_detected_by_default(self) -> None:
        result = make_evaluation_result()
        assert result.regression_detected is False
        assert result.previous_score is None

    def test_guideline_comparison_defaults_empty(self) -> None:
        result = make_evaluation_result()
        assert result.guideline_comparison.met == []
        assert result.guideline_comparison.missed == []
