from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from PIL import Image

from holodeck.agents.video.ai_compositor import AICompositor


def _make_fake_image(width: int = 128, height: int = 128) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _fake_image_result(
    image_data: bytes | None = None,
    width: int = 128,
    height: int = 128,
) -> dict[str, Any]:
    return {
        "image_data": image_data or _make_fake_image(width, height),
        "width": width,
        "height": height,
        "cache_key": "fake",
        "provider": "test",
    }


def test_generate_background_returns_image() -> None:
    provider = MagicMock()
    provider.generate.return_value = _fake_image_result()

    context: dict[str, Any] = {}
    comp = AICompositor(provider=provider, context=context)

    result = comp.generate_background("scene1", "kitchen", mood="warm")

    assert result is not None
    assert isinstance(result, Image.Image)
    assert context["ai_background_assets"]["scene1"] is not None
    provider.generate.assert_called_once()


def test_generate_background_returns_none_on_failure() -> None:
    provider = MagicMock()
    provider.generate.return_value = None

    context: dict[str, Any] = {}
    comp = AICompositor(provider=provider, context=context)

    result = comp.generate_background("scene2", "bedroom")
    assert result is None
    assert "ai_background_assets" not in context


def test_generate_character_stores_in_context() -> None:
    provider = MagicMock()
    provider.generate.return_value = _fake_image_result()

    context: dict[str, Any] = {}
    comp = AICompositor(provider=provider, context=context)

    result = comp.generate_character("Rachel", "scene1", "friendly waitress")

    assert result is not None
    assert isinstance(result, Image.Image)
    assert result.mode == "RGBA"
    assert context["ai_character_assets"]["scene1"]["Rachel"] is not None


def test_generate_character_uses_seed() -> None:
    provider = MagicMock()
    provider.generate.return_value = _fake_image_result()

    comp = AICompositor(provider=provider, context={})

    comp.generate_character("Rachel", "s1", "desc", production_id="p1")
    seed1 = provider.generate.call_args.kwargs["seed"]
    assert isinstance(seed1, int)

    provider.generate.reset_mock()
    provider.generate.return_value = _fake_image_result()

    comp.generate_character("Monica", "s1", "desc", production_id="p1")
    seed2 = provider.generate.call_args.kwargs["seed"]

    assert seed1 != seed2


def test_compose_frame_with_background_and_one_character() -> None:
    comp = AICompositor(provider=MagicMock(), context={})
    bg = Image.new("RGB", (256, 256), (0, 0, 255))
    char = Image.new("RGBA", (64, 64), (255, 0, 0, 255))

    result = comp.compose_frame(bg, [(char, 50, 50, 1.0)])

    assert result is not None
    assert result.endswith(".png")
    with open(result, "rb") as f:
        header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n"


def test_compose_frame_returns_none_on_no_background() -> None:
    comp = AICompositor(provider=MagicMock())
    result = comp.compose_frame(None, [])
    assert result is None


def test_compose_frame_handles_single_character() -> None:
    comp = AICompositor(provider=MagicMock())
    bg = Image.new("RGB", (100, 100), (0, 255, 0))
    char = Image.new("RGBA", (30, 30), (0, 0, 255, 200))

    result = comp.compose_frame(bg, [(char, 10, 10, 0.5)])

    assert result is not None
    assert result.endswith(".png")
    with open(result, "rb") as f:
        header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n"


def test_compose_frame_respects_scale() -> None:
    comp = AICompositor(provider=MagicMock())
    bg = Image.new("RGB", (200, 200), (0, 0, 0))
    char = Image.new("RGBA", (100, 100), (255, 255, 255, 128))

    result = comp.compose_frame(bg, [(char, 0, 0, 2.0)])

    assert result is not None
    assert result.endswith(".png")


def test_compose_frame_skips_none_character() -> None:
    comp = AICompositor(provider=MagicMock())
    bg = Image.new("RGB", (100, 100), (0, 0, 0))

    result = comp.compose_frame(bg, [(None, 0, 0, 1.0)])
    assert result is not None
