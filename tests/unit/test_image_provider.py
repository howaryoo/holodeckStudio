from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from holodeck.agents.video.image_provider import (
    AiBudgetTracker,
    ImageProvider,
    ReplicateProvider,
    SvgFallbackProvider,
    _make_seed,
)


def test_svg_fallback_provider_returns_none() -> None:
    p = SvgFallbackProvider()
    assert p.generate("test") is None


def test_replicate_provider_satisfies_protocol() -> None:
    p = ReplicateProvider(api_key="fake")
    assert isinstance(p, ImageProvider)


def test_replicate_provider_returns_none_on_api_error() -> None:
    mock_client = MagicMock()
    mock_client.run.side_effect = RuntimeError("API down")
    with patch("replicate.client.Client", return_value=mock_client):
        p = ReplicateProvider(api_key="fake")
        result = p.generate("test prompt")
        assert result is None


def test_replicate_provider_returns_image_on_success() -> None:
    fake_bytes = b"PNG...fake"
    mock_response = MagicMock()
    mock_response.content = fake_bytes
    mock_response.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.run.return_value = ["https://fake.img/png"]

    with (
        patch("replicate.client.Client", return_value=mock_client),
        patch("httpx.get", return_value=mock_response),
    ):
        p = ReplicateProvider(api_key="fake", model="test/model", num_inference_steps=1)
        result = p.generate("test prompt", width=512, height=512, seed=42)

    assert result is not None
    assert result["image_data"] == fake_bytes
    assert result["width"] == 512
    assert result["height"] == 512
    assert result["provider"] == "replicate"
    assert result["cache_key"]


def test_replicate_provider_enforces_budget() -> None:
    context: dict[str, Any] = {"ai_budget_used": 0}
    budget = AiBudgetTracker(limit=1, context=context)
    p = ReplicateProvider(api_key="fake", budget_tracker=budget)

    mock_client = MagicMock()
    mock_client.run.return_value = ["https://fake.img/png"]

    with (
        patch("replicate.client.Client", return_value=mock_client),
        patch("httpx.get") as mock_get,
    ):
        mock_resp = MagicMock()
        mock_resp.content = b"img1"
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result1 = p.generate("prompt 1")
        assert result1 is not None
        assert context["ai_budget_used"] == 1

        result2 = p.generate("prompt 2")
        assert result2 is None
        assert context["ai_budget_used"] == 1


def test_ai_budget_tracker_deduct() -> None:
    context: dict[str, Any] = {"ai_budget_used": 0}
    tracker = AiBudgetTracker(limit=3, context=context)

    assert tracker.deduct() is True
    assert context["ai_budget_used"] == 1
    assert tracker.deduct() is True
    assert context["ai_budget_used"] == 2
    assert tracker.deduct() is True
    assert context["ai_budget_used"] == 3
    assert tracker.deduct() is False
    assert context["ai_budget_used"] == 3


def test_ai_budget_tracker_unlimited() -> None:
    tracker = AiBudgetTracker(limit=0)
    for _ in range(100):
        assert tracker.deduct() is True


def test_ai_budget_tracker_no_context_is_unlimited() -> None:
    tracker = AiBudgetTracker(limit=1)
    for _ in range(10):
        assert tracker.deduct() is True


def test_seed_determinism() -> None:
    s1 = _make_seed("Rachel Green", "prod-1")
    s2 = _make_seed("Rachel Green", "prod-1")
    assert s1 == s2


def test_seed_different_characters() -> None:
    s1 = _make_seed("Rachel", "prod-1")
    s2 = _make_seed("Monica", "prod-1")
    assert s1 != s2


def test_seed_different_productions() -> None:
    s1 = _make_seed("Rachel", "prod-1")
    s2 = _make_seed("Rachel", "prod-2")
    assert s1 != s2
