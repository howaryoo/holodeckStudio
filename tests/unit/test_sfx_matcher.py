from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from holodeck.agents.audio.sfx_library import SFXRegistry
from holodeck.agents.audio.sfx_matcher import SFXMatcher

SAMPLE_SOUND_DESIGN = """
SCENE 1: Sickbay
- AMBIENCE: medical bay hum, quiet beeping
- FOLEY: footsteps on deck plates
- SFX: door hiss, hypospray application

SCENE 2: Voyager Bridge
- AMBIENCE: bridge operations, computer chatter
- FOLEY: console keypresses
- SFX: hailing frequencies, turbolift arrival
"""

SAMPLE_SINGLE_SCENE = """
SCENE 1: Holodeck
- AMBIENCE: holodeck ambient hum
- FOLEY: footsteps
- SFX: program activation
"""


def _make_registry(tmpdir: str, entries: list[dict]) -> SFXRegistry:
    index_path = f"{tmpdir}/index.json"
    with open(index_path, "w") as f:
        json.dump(entries, f)
    return SFXRegistry(library_path=tmpdir)


def test_parse_sound_design_blocks():
    with tempfile.TemporaryDirectory() as td:
        r = _make_registry(td, [])
        m = SFXMatcher(r)
        cues = m.parse_sound_design(SAMPLE_SOUND_DESIGN)
        assert len(cues) == 2
        assert cues[0].scene_number == 1
        assert cues[0].location == "Sickbay"
        assert cues[1].scene_number == 2
        assert cues[1].location == "Voyager Bridge"


def test_parse_ambience_foley_sfx_lines():
    with tempfile.TemporaryDirectory() as td:
        r = _make_registry(td, [])
        m = SFXMatcher(r)
        cues = m.parse_sound_design(SAMPLE_SOUND_DESIGN)
        assert "medical bay hum" in cues[0].ambience
        assert "footsteps" in cues[0].foley
        assert "hypospray application" in cues[0].sfx[1]
        assert "door hiss" in cues[0].sfx[0]


def test_parse_single_scene():
    with tempfile.TemporaryDirectory() as td:
        r = _make_registry(td, [])
        m = SFXMatcher(r)
        cues = m.parse_sound_design(SAMPLE_SINGLE_SCENE)
        assert len(cues) == 1
        assert cues[0].location == "Holodeck"
        assert "holodeck ambient hum" in cues[0].ambience


def test_parse_empty_text():
    with tempfile.TemporaryDirectory() as td:
        r = _make_registry(td, [])
        m = SFXMatcher(r)
        assert m.parse_sound_design("") == []
        assert m.parse_sound_design("  ") == []
        assert m.parse_sound_design("No scene blocks here") == []


def test_match_cues_finds_files():
    with tempfile.TemporaryDirectory() as td:
        # Create actual files so _resolve() finds them
        os.makedirs(f"{td}/background", exist_ok=True)
        os.makedirs(f"{td}/doors", exist_ok=True)
        os.makedirs(f"{td}/medical", exist_ok=True)
        for f in ["background/tng_sickbay.mp3", "doors/tng_door_open.mp3", "medical/hypospray_1.mp3"]:
            Path(f"{td}/{f}").touch()
        r = _make_registry(td, [
            {"path": "background/tng_sickbay.mp3", "category": "background",
             "filename": "tng_sickbay", "tags": ["background", "sickbay", "medical"],
             "duration": 30.0, "is_loopable": True},
            {"path": "doors/tng_door_open.mp3", "category": "doors",
             "filename": "tng_door_open", "tags": ["door", "open", "hiss"],
             "duration": 1.0, "is_loopable": False},
            {"path": "medical/hypospray_1.mp3", "category": "medical",
             "filename": "hypospray_1", "tags": ["hypospray", "medical", "injection"],
             "duration": 1.0, "is_loopable": False},
        ])
        m = SFXMatcher(r)
        cues = m.parse_sound_design("SCENE 1: Sickbay\n- AMBIENCE: sickbay hum\n- FOLEY: \n- SFX: hypospray")
        matched = m.match_cues(cues)
        assert len(matched) == 1
        assert matched[0].ambience_path is not None
        assert "tng_sickbay" in matched[0].ambience_path


def test_match_cues_partial_no_crash():
    with tempfile.TemporaryDirectory() as td:
        r = _make_registry(td, [
            {"path": "background/hum.mp3", "category": "background",
             "filename": "hum", "tags": ["background", "hum"],
             "duration": 10.0, "is_loopable": True},
        ])
        m = SFXMatcher(r)
        cues = m.parse_sound_design("SCENE 1: Planet X\n- AMBIENCE: alien wind\n- FOLEY: \n- SFX: quantum torpedo, tricorder")
        matched = m.match_cues(cues)
        assert len(matched) == 1
        # ambience might match or not
        # sfx should return empty for non-matching items


def test_match_cues_all_unmatched_returns_none_paths():
    with tempfile.TemporaryDirectory() as td:
        r = _make_registry(td, [])
        m = SFXMatcher(r)
        cues = m.parse_sound_design("SCENE 1: Nowhere\n- AMBIENCE: nothing\n- FOLEY: \n- SFX: xyzzy")
        matched = m.match_cues(cues)
        assert len(matched) == 1
        assert matched[0].ambience_path is None
        assert matched[0].sfx_paths == []
        assert matched[0].foley_paths == []
