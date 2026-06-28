from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from holodeck.agents.audio.sfx_library import SFXEntry
from holodeck.agents.audio.sfx_matcher import SFXMatcher
from holodeck.agents.audio.sfx_library import SFXRegistry
from holodeck.agents.audio.audio_mixer import AudioMixer
from holodeck.pipeline.runner import ProductionPipeline


def _make_fake_index(tmp: Path) -> Path:
    entries = [
        {
            "path": "background/hum.mp3",
            "category": "background",
            "filename": "hum.mp3",
            "tags": ["background", "hum", "ambience", "bridge", "starship"],
            "duration": 10.0,
            "is_loopable": True,
        },
        {
            "path": "doors/door.mp3",
            "category": "doors",
            "filename": "door.mp3",
            "tags": ["door", "bridge", "sfx"],
            "duration": 1.5,
            "is_loopable": False,
        },
    ]
    idx_path = tmp / "index.json"
    with open(str(idx_path), "w") as f:
        json.dump(entries, f)
    return idx_path


def _make_fake_mp3(p: Path, duration_sec: float = 1.0) -> None:
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
         "-t", str(duration_sec), str(p)],
        capture_output=True,
    )


@pytest.mark.asyncio
class TestSFXPipeline:
    async def test_sfx_matcher_parses_sound_design(self):
        registry = SFXRegistry()
        matcher = SFXMatcher(registry)
        sound_design = """
SCENE 1: Bridge
- AMBIENCE: Quiet hum of starship engines
- FOLEY: Footsteps on metal deck
- SFX: Door opening, console beep

SCENE 2: Sickbay
- AMBIENCE: Medical equipment beeping
- SFX: Hypospray hiss
"""
        cues = matcher.parse_sound_design(sound_design)
        assert len(cues) == 2
        assert cues[0].scene_number == 1
        assert "bridge" in cues[0].ambience.lower() or "starship" in cues[0].ambience.lower()
        assert len(cues[0].sfx) >= 2

    async def test_audio_mixer_mixes_scene(self):
        with tempfile.TemporaryDirectory() as td:
            dia = os.path.join(td, "dialogue.mp3")
            amb = os.path.join(td, "ambience.mp3")
            out = os.path.join(td, "output.mp3")
            _make_fake_mp3(dia, 1.0)
            _make_fake_mp3(amb, 3.0)
            mixer = AudioMixer()
            result = mixer.mix_scene(
                dialogue_path=dia, ambience_path=amb,
                output_path=out, scene_duration=2.0,
            )
            assert result == out
            assert os.path.exists(out)
            assert os.path.getsize(out) > 0

    async def test_audio_mixer_mixes_scene_with_sfx(self):
        with tempfile.TemporaryDirectory() as td:
            dia = os.path.join(td, "dialogue.mp3")
            amb = os.path.join(td, "ambience.mp3")
            sfx1 = os.path.join(td, "sfx1.mp3")
            out = os.path.join(td, "output.mp3")
            _make_fake_mp3(dia, 1.0)
            _make_fake_mp3(amb, 3.0)
            _make_fake_mp3(sfx1, 0.5)
            mixer = AudioMixer()
            result = mixer.mix_scene(
                dialogue_path=dia, ambience_path=amb,
                sfx_paths=[sfx1],
                output_path=out, scene_duration=2.0,
            )
            assert result == out
            assert os.path.exists(out)
            assert os.path.getsize(out) > 0

    async def test_audio_mixer_concat_scenes(self):
        with tempfile.TemporaryDirectory() as td:
            s1 = os.path.join(td, "scene1.mp3")
            s2 = os.path.join(td, "scene2.mp3")
            out = os.path.join(td, "full.mp3")
            _make_fake_mp3(s1, 1.0)
            _make_fake_mp3(s2, 1.0)
            mixer = AudioMixer()
            result = mixer.concat_scenes([s1, s2], out)
            assert result == out
            assert os.path.exists(out)
            assert os.path.getsize(out) > 0

    async def test_audio_mixer_dialogue_only_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            dia = os.path.join(td, "dialogue.mp3")
            out = os.path.join(td, "output.mp3")
            _make_fake_mp3(dia, 1.0)
            mixer = AudioMixer()
            result = mixer.mix_scene(
                dialogue_path=dia, ambience_path=None,
                output_path=out, scene_duration=1.0,
            )
            assert result == out
            assert os.path.exists(out)

    async def test_sfx_registry_search_real_index(self):
        registry = SFXRegistry()
        assert len(registry.entries) > 0
        results = registry.search("door")
        assert len(results) > 0
        assert any("door" in e.filename.lower() for e in results)

    async def test_empty_library_graceful(self):
        with tempfile.TemporaryDirectory() as td:
            idx = os.path.join(td, "index.json")
            with open(idx, "w") as f:
                json.dump([], f)
            registry = SFXRegistry(library_path=td)
            assert len(registry.entries) == 0
            assert registry.search("anything") == []
            assert registry.get_ambience("Bridge") is None
