from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from holodeck.agents.video.frame_renderer import (
    _parse_characters,
    _parse_scenes,
    _suggest_pose,
)

# --- helper ---

_SAMPLE_ANIMATION = """SCENE 1: Coffee House
Rachel: I cannot believe he did that.
Monica: I know, right?

SCENE 2: Apartment
Ross: Hey, what's up?
"""

_SAMPLE_CHARACTERS = """CHARACTER: Rachel Green
BODY: Slim, stylish
FACE: Friendly, expressive

CHARACTER: Monica Geller
BODY: Athletic
"""


class TestParseScenes:
    def test_parses_two_scenes(self) -> None:
        scenes = _parse_scenes(_SAMPLE_ANIMATION)
        assert len(scenes) == 2

    def test_scene_has_number_location_lines(self) -> None:
        scenes = _parse_scenes(_SAMPLE_ANIMATION)
        s1 = scenes[0]
        assert s1["number"] == "1"
        assert s1["location"] == "Coffee House"
        assert len(s1["lines"]) == 2

    def test_empty_text_returns_default(self) -> None:
        scenes = _parse_scenes("")
        assert len(scenes) == 1
        assert scenes[0]["number"] == "1"

    def test_unknown_location(self) -> None:
        scenes = _parse_scenes("just some text\nmore text")
        assert scenes[0]["location"] == "unknown"


class TestParseCharacters:
    def test_character_from_designs(self) -> None:
        chars = _parse_characters(_SAMPLE_CHARACTERS, "")
        assert any("Rachel" in c for c in chars)
        assert any("Monica" in c for c in chars)

    def test_character_from_script(self) -> None:
        chars = _parse_characters("", _SAMPLE_ANIMATION)
        assert "Rachel" in chars
        assert "Monica" in chars
        assert "Ross" in chars

    def test_no_text_returns_default(self) -> None:
        chars = _parse_characters("", "")
        assert chars == ["Character"]

    def test_known_headers_excluded(self) -> None:
        text = "CHARACTER: Test\nBODY: Slim\nHEIGHT: Tall"
        chars = _parse_characters(text)
        assert any("Test" in c for c in chars)
        assert len(chars) == 1


class TestSuggestPose:
    def test_walking_pose(self) -> None:
        assert _suggest_pose(["She walks into the room"]) == "walking"

    def test_standing_pose(self) -> None:
        assert _suggest_pose(["He stands there"]) == "standing"

    def test_empty_returns_standing(self) -> None:
        assert _suggest_pose([]) == "standing"


class TestAiCompositorSetup:
    def test_svgonly_returns_none(self) -> None:
        from holodeck.agents.video.frame_renderer import FrameRendererAgent

        agent = FrameRendererAgent()
        compositor = agent._setup_ai_compositor({"image_provider": "svgonly"})
        assert compositor is None

    def test_missing_api_key_returns_none(self) -> None:
        from holodeck.agents.video.frame_renderer import FrameRendererAgent

        agent = FrameRendererAgent()
        fake_settings = MagicMock()
        fake_settings.replicate_api_key = ""
        fake_settings.ai_budget_limit = 25
        with patch(
            "holodeck.config.settings.Settings",
            return_value=fake_settings,
        ):
            compositor = agent._setup_ai_compositor({"image_provider": "replicate"})
        assert compositor is None

    def test_replicate_provider_creates_compositor(self) -> None:
        from holodeck.agents.video.frame_renderer import FrameRendererAgent

        agent = FrameRendererAgent()
        fake_settings = MagicMock()
        fake_settings.replicate_api_key = "fake_key"
        fake_settings.ai_budget_limit = 25
        with patch(
            "holodeck.config.settings.Settings",
            return_value=fake_settings,
        ):
            compositor = agent._setup_ai_compositor({"image_provider": "replicate"})
        assert compositor is not None
        assert hasattr(compositor, "_provider")


class TestProcessMetadata:
    def test_svg_fallback_count_in_metadata(self) -> None:
        from holodeck.agents.video.frame_renderer import FrameRendererAgent

        agent = FrameRendererAgent()
        context = {
            "script": "Rachel: Hello\nMonica: Hi",
            "animation": "SCENE 1: Cafe\nRachel: Hello\nMonica: Hi",
            "character_designs": "CHARACTER: Rachel\nCHARACTER: Monica",
            "character_visuals": {},
            "image_provider": "svgonly",
            "sub_frames": 2,
        }
        output = agent.process(context)

        md = output.metadata
        assert md is not None
        assert md.get("svg_fallback_count") == 0
        assert md.get("image_provider") == "svgonly"
        assert md.get("ai_characters") == 0
        assert md.get("ai_backgrounds") == 0

    def test_ai_metadata_present_when_compositor_active(self, tmp_path: Path) -> None:
        from holodeck.agents.video.frame_renderer import FrameRendererAgent

        agent = FrameRendererAgent()

        fake_compositor = MagicMock()
        fake_compositor.generate_background.return_value = MagicMock()
        fake_compositor.generate_character.return_value = MagicMock()
        fake_compositor.compose_frame.return_value = str(tmp_path / "fake_frame.png")

        context = {
            "script": "Rachel: Hello",
            "animation": "SCENE 1: Cafe\nRachel: Hello",
            "character_designs": "CHARACTER: Rachel",
            "character_visuals": {},
            "image_provider": "replicate",
            "sub_frames": 2,
        }

        with patch.object(
            agent, "_setup_ai_compositor", return_value=fake_compositor,
        ):
            output = agent.process(context)

        md = output.metadata
        assert md is not None
        assert md["image_provider"] == "replicate"
        assert md["ai_backgrounds"] == 1
        assert md["ai_characters"] == 1
        assert md["svg_fallback_count"] == 0

    def test_ai_fallback_to_svg_when_generation_fails(self) -> None:
        from holodeck.agents.video.frame_renderer import FrameRendererAgent

        agent = FrameRendererAgent()

        fake_compositor = MagicMock()
        fake_compositor.generate_background.return_value = None
        fake_compositor.generate_character.return_value = None

        context = {
            "script": "Rachel: Hello",
            "animation": "SCENE 1: Cafe\nRachel: Hello",
            "character_designs": "CHARACTER: Rachel",
            "character_visuals": {},
            "image_provider": "replicate",
            "sub_frames": 2,
        }

        with patch.object(
            agent, "_setup_ai_compositor", return_value=fake_compositor,
        ):
            output = agent.process(context)

        md = output.metadata
        assert md is not None
        assert md["svg_fallback_count"] > 0
        assert md["ai_backgrounds"] == 0
        assert md["ai_characters"] == 0
