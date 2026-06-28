from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from holodeck.evaluation.schemas import (
    REJECTION_THRESHOLD,
    DimensionScore,
    EvaluationDimension,
    EvaluationResult,
    GoldenDatasetEntry,
    QualityGuidelines,
    ScopeBoundaries,
)


def make_entry(prompt_id: str = "test-entry-001") -> GoldenDatasetEntry:
    return GoldenDatasetEntry(
        prompt_id=prompt_id,
        user_prompt="Monica discovers a rival chef.",
        quality_guidelines=QualityGuidelines(
            narrative_goal="Monica's competitiveness resolves with warmth.",
            character_arcs={"Monica": "competitive → self-aware"},
            comedy_approach="Escalating situational comedy",
            emotional_beats=["excitement", "chaos", "warmth"],
            production_constraints=["Max 2 sets"],
            thematic_focus="Competitiveness vs self-acceptance",
        ),
        scope_boundaries=ScopeBoundaries(
            must_include=["Monica in kitchen"],
            must_exclude=["Ross dinosaur subplot"],
            character_focus=["Monica", "Chandler"],
        ),
        acceptable_variations=["Rival can be male or female"],
    )


def make_dimension_scores(score: float = 0.8) -> list[DimensionScore]:
    return [
        DimensionScore(
            dimension=dim,
            score=score,
            weight=meta["weight"],
            reasoning=f"Test reasoning for {dim}",
            evidence=[f"Evidence for {dim}"],
        )
        for dim, meta in EvaluationDimension.DIMENSIONS.items()
    ]


def make_mock_agent_output(score: float = 0.8) -> MagicMock:
    from holodeck.agents.base import AgentOutput

    scores = make_dimension_scores(score)
    return AgentOutput(
        content="[]",
        metadata={"dimension_scores": [s.model_dump() for s in scores]},
    )


class TestEvaluationResultStructure:
    def test_exactly_eight_dimension_scores(self) -> None:
        scores = make_dimension_scores()
        assert len(scores) == 8

    def test_overall_score_weighted_sum(self) -> None:
        scores = make_dimension_scores(score=1.0)
        total = sum(ds.weighted_score for ds in scores)
        assert abs(total - 1.0) < 1e-9

    def test_passed_quality_gate_true_above_threshold(self) -> None:
        scores = make_dimension_scores(score=0.8)
        overall = sum(ds.weighted_score for ds in scores)
        result = EvaluationResult(
            script_id="s1",
            golden_entry_id="e1",
            dimension_scores=scores,
            passed_quality_gate=overall >= REJECTION_THRESHOLD,
        )
        assert result.passed_quality_gate is True

    def test_passed_quality_gate_false_below_threshold(self) -> None:
        scores = make_dimension_scores(score=0.1)
        overall = sum(ds.weighted_score for ds in scores)
        result = EvaluationResult(
            script_id="s1",
            golden_entry_id="e1",
            dimension_scores=scores,
            passed_quality_gate=overall >= REJECTION_THRESHOLD,
        )
        assert result.passed_quality_gate is False

    def test_red_flags_populated_from_triggered_flags(self) -> None:
        scores = make_dimension_scores()
        result = EvaluationResult(
            script_id="s1",
            golden_entry_id="e1",
            dimension_scores=scores,
            passed_quality_gate=True,
            red_flags_triggered=["Joey shares food willingly", "Story ends without resolution"],
        )
        assert len(result.red_flags_triggered) == 2

    def test_regression_detection_fields_default(self) -> None:
        scores = make_dimension_scores()
        result = EvaluationResult(
            script_id="s1",
            golden_entry_id="e1",
            dimension_scores=scores,
            passed_quality_gate=True,
        )
        assert result.previous_score is None
        assert result.regression_detected is False

    def test_regression_detected_when_score_drops_over_ten_percent(self) -> None:
        previous = 0.80
        current = 0.70
        regression = (previous - current) / previous > 0.10
        assert regression is True

    def test_no_regression_within_ten_percent(self) -> None:
        previous = 0.80
        current = 0.75
        regression = (previous - current) / previous > 0.10
        assert regression is False


class TestJudgeAgentParsing:
    def test_parse_dimension_scores_from_json(self) -> None:
        import json
        from holodeck.agents.evaluation.judge import _parse_dimension_scores

        scores_data = [
            {
                "dimension": dim,
                "score": 0.8,
                "weight": meta["weight"],
                "reasoning": "Good",
                "evidence": ["example"],
            }
            for dim, meta in EvaluationDimension.DIMENSIONS.items()
        ]
        content = json.dumps(scores_data)
        scores = _parse_dimension_scores(content)
        assert len(scores) == 8

    def test_parse_raises_on_wrong_count(self) -> None:
        import json
        from holodeck.agents.evaluation.judge import _parse_dimension_scores

        content = json.dumps([{"dimension": "x", "score": 0.5, "weight": 1.0}])
        with pytest.raises(ValueError, match="Expected 8"):
            _parse_dimension_scores(content)

    def test_parse_raises_on_no_json(self) -> None:
        from holodeck.agents.evaluation.judge import _parse_dimension_scores

        with pytest.raises(ValueError, match="No JSON array"):
            _parse_dimension_scores("this is not json")
