from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ai_context(tmp_path: Path) -> dict[str, Any]:
    d = tmp_path / "ai_frames"
    d.mkdir()
    f0 = d / "frame_0.png"
    f1 = d / "frame_1.png"
    f0.write_bytes(b"PNG...0")
    f1.write_bytes(b"PNG...1")
    return {
        "ai_composited_frames": {0: str(f0), 1: str(f1)},
        "subtitle_data": [{"frame_index": 0, "dialogue_text": "Hello"}],
        "frame_svgs": "",
        "dialogue_audio_urls": [],
        "scene_moods": {"1": "warm"},
        "output_dir": str(tmp_path / "output"),
        "production_id": "test-p1",
        "episode_id": "e1",
    }


class TestVideoAssemblerAiMetadata:
    def test_enhancement_type_ai_composited(self, ai_context: dict[str, Any]) -> None:
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()

        with (
            patch("holodeck.agents.video.video_assembler._has_ffmpeg", return_value=True),
            patch("subprocess.run") as mock_run,
            patch("os.makedirs"),
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2"),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = b""
            mock_proc.stderr = b""
            mock_run.return_value = mock_proc

            output = agent.process(ai_context)

        md = output.metadata
        assert md is not None
        assert md["enhancement_type"] == "ai_composited"

    def test_enhancement_type_svg_when_no_ai(self, tmp_path: Path) -> None:
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        ctx = {
            "frame_svgs": "<svg>test</svg>",
            "subtitle_data": [{"frame_index": 0, "dialogue_text": "Hello"}],
            "dialogue_audio_urls": [],
            "scene_moods": {},
            "output_dir": str(tmp_path / "svg_out"),
            "production_id": "test-p2",
            "episode_id": "e2",
        }

        with (
            patch("holodeck.agents.video.video_assembler._has_ffmpeg", return_value=True),
            patch("subprocess.run") as mock_run,
            patch("os.makedirs"),
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2"),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = b""
            mock_proc.stderr = b""
            mock_run.return_value = mock_proc

            output = agent.process(ctx)

        md = output.metadata
        assert md is not None
        assert md["enhancement_type"] == "svg"

    def test_ai_frames_sorted_by_index(self, tmp_path: Path) -> None:
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        d = tmp_path / "frame_src"
        d.mkdir()
        for name in ("f1.png", "f3.png", "f5.png"):
            (d / name).write_bytes(b"PNG...")

        ctx = {
            "ai_composited_frames": {
                5: str(d / "f5.png"),
                1: str(d / "f1.png"),
                3: str(d / "f3.png"),
            },
            "subtitle_data": [{"frame_index": 0, "dialogue_text": "Hello"}],
            "frame_svgs": "",
            "dialogue_audio_urls": [],
            "scene_moods": {"1": "warm"},
            "output_dir": str(tmp_path / "output2"),
            "production_id": "test-p1",
            "episode_id": "e1",
        }

        agent = VideoAssemblerAgent()

        with (
            patch("holodeck.agents.video.video_assembler._has_ffmpeg", return_value=True),
            patch("subprocess.run") as mock_run,
            patch("os.makedirs"),
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2"),
        ):
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = b""
            mock_proc.stderr = b""
            mock_run.return_value = mock_proc

            agent.process(ctx)


class TestVideoAssemblerAiValidate:
    def test_validate_rejects_ai_without_frames_or_audio(self, ai_context: dict[str, Any]) -> None:
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        result = agent.validate_input(ai_context)
        assert result.valid is False

    def test_validate_accepts_ai_context_with_audio(self, ai_context: dict[str, Any]) -> None:
        from holodeck.agents.video.video_assembler import VideoAssemblerAgent

        agent = VideoAssemblerAgent()
        ctx = dict(ai_context)
        ctx["dialogue_audio_urls"] = ["/fake/audio.mp3"]
        result = agent.validate_input(ctx)
        assert result.valid is True
