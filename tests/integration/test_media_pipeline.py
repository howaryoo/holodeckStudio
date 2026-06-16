from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from holodeck.agents.base import AgentOutput
from holodeck.pipeline.runner import ProductionPipeline
from holodeck.pipeline.stages import StageType


class _MockAgent:
    stage = StageType.REVIEW

    def validate_input(self, context):
        from holodeck.agents.base import ValidationResult
        return ValidationResult(valid=True)

    def process(self, context):
        name = getattr(self, "_name", "unknown")
        return AgentOutput(content=f"Output from {name}")

    def review_output(self, output):
        from holodeck.agents.base import ReviewResult
        return ReviewResult(approved=True, score=85, feedback="good")


def _make_mock(name: str) -> _MockAgent:
    a = _MockAgent()
    a._name = name
    a.stage = StageType.REVIEW
    return a


@pytest.mark.asyncio
class TestMediaPipeline:
    async def test_media_agents_wired_in_pipeline(self):
        """Verify media agents are wired as stages 20-22."""
        pipeline = ProductionPipeline()
        assert pipeline.voice_synth is not None
        assert pipeline.frame_renderer is not None
        assert pipeline.video_assembler is not None

    async def test_voice_synthesis_parses_dialogue(self):
        from holodeck.agents.audio.voice_synthesis import _parse_dialogue_lines

        script = "HERO: Hello world!\nVILLAIN: Not today!\n"
        lines = _parse_dialogue_lines(script)
        assert len(lines) == 2
        assert lines[0] == ("HERO", "Hello world!")
        assert lines[1] == ("VILLAIN", "Not today!")

    async def test_voice_synthesis_narrator_fallback(self):
        from holodeck.agents.audio.voice_synthesis import _parse_dialogue_lines

        script = "Once upon a time in a galaxy far away.\nIt was a dark night."
        lines = _parse_dialogue_lines(script)
        assert lines
        assert all(char == "Narrator" for char, _ in lines)

    async def test_frame_renderer_parses_scenes(self):
        from holodeck.agents.video.frame_renderer import _parse_scenes

        anim = "SCENE 1: Bridge\nHero enters.\nSCENE 2: Engine Room\nVillain waits.\n"
        scenes = _parse_scenes(anim)
        assert len(scenes) == 2
        assert scenes[0]["location"] == "Bridge"
        assert scenes[1]["number"] == "2"

    async def test_frame_renderer_generates_svg(self):
        from holodeck.agents.video.frame_renderer import _build_scene_svg

        svg = _build_scene_svg("1", "Bridge", ["Hero enters."], ["HERO"])
        assert "<svg" in svg
        assert "Hero" in svg or "HERO" in svg
        assert "</svg>" in svg

    async def test_video_assembler_validate_no_frames(self):
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        result = agent.validate_input({})
        assert not result.valid

    async def test_video_assembler_returns_error_on_no_frames(self):
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        result = agent.process({"production_id": "test"})
        assert "No frames" in result.content

    @patch("holodeck.agents.audio.voice_synthesis._has_piper", return_value=False)
    @patch("holodeck.agents.audio.voice_synthesis._has_gtts", return_value=False)
    async def test_voice_synthesis_no_gtts(self, mock_gtts, mock_piper):
        from holodeck.agents.audio.voice_synthesis import VoiceSynthesisAgent

        agent = VoiceSynthesisAgent()
        result = agent.process({"script": "HERO: test\n"})
        assert result.metadata is not None
        assert result.metadata.get("tts_engine") == "none"

    @patch("holodeck.agents.video.video_assembler._has_ffmpeg", return_value=False)
    async def test_video_assembler_no_ffmpeg(self, mock_has):
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        result = agent.process({"frame_svgs": "<svg></svg>\n---NEXT FRAME---\n<svg></svg>", "production_id": "p1", "output_dir": "/tmp"})
        assert "not found" in result.content.lower() or "install" in result.content.lower()

    @patch("holodeck.agents.video.video_assembler._has_ffmpeg", return_value=True)
    @patch("holodeck.agents.video.video_assembler.subprocess.run")
    async def test_video_assembler_calls_imagemagick(self, mock_run, mock_ffmpeg):
        def _side_effect(*args, **kwargs):
            proc = MagicMock()
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and len(cmd) > 1:
                if "convert" in cmd[0] and len(cmd) > 2:
                    png_path = cmd[-1]
                    os.makedirs(os.path.dirname(png_path), exist_ok=True)
                    Path(png_path).touch()
                if "ffmpeg" in cmd[0]:
                    out_idx = cmd.index(cmd[-1])
                    out_path = cmd[-1]
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    Path(out_path).touch()
            proc.returncode = 0
            proc.stderr = b""
            return proc

        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        mock_run.side_effect = _side_effect
        agent = VideoAssemblerAgent()
        result = agent.process({
            "frame_svgs": "<svg><rect/></svg>\n---NEXT FRAME---\n<svg><circle/></svg>",
            "production_id": "p1",
            "episode_id": "e1",
            "output_dir": "/tmp",
            "dialogue_audio_urls": [],
        })
        calls = [c[0][0] for c in mock_run.call_args_list]
        convert_calls = [c for c in calls if isinstance(c, list) and "convert" in c[0]]
        ffmpeg_calls = [c for c in calls if isinstance(c, list) and "ffmpeg" in c[0]]
        assert len(convert_calls) >= 1, "Expected at least one convert call"
        assert len(ffmpeg_calls) >= 1, "Expected at least one ffmpeg call"

    @patch("holodeck.agents.video.video_assembler._has_ffmpeg", return_value=True)
    @patch("holodeck.agents.video.video_assembler.subprocess.run", return_value=MagicMock(returncode=1, stderr=b"error"))
    async def test_video_assembler_handles_ffmpeg_failure(self, mock_run, mock_ffmpeg):
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        result = agent.process({
            "frame_svgs": "<svg><rect/></svg>\n---NEXT FRAME---\n<svg><circle/></svg>",
            "production_id": "p1",
            "episode_id": "e1",
            "output_dir": "/tmp",
            "dialogue_audio_urls": [],
        })
        assert "failed" in result.content.lower() or "No frames" in result.content
