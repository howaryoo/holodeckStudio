from __future__ import annotations

import json
import tempfile
from pathlib import Path

from holodeck.agents.audio.sfx_library import SFXRegistry


def _make_index(tmpdir: Path, entries: list[dict]) -> Path:
    index_path = tmpdir / "index.json"
    with open(index_path, "w") as f:
        json.dump(entries, f)
    return tmpdir


def test_registry_loads_index():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "doors/door.mp3", "category": "doors", "filename": "door",
             "tags": ["door", "open"], "duration": 1.5, "is_loopable": False},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        assert len(r.entries) == 1
        assert r.entries[0].filename == "door"


def test_search_by_keyword():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "doors/door.mp3", "category": "doors", "filename": "door",
             "tags": ["door", "open"], "duration": 1.5, "is_loopable": False},
            {"path": "background/hum.mp3", "category": "background", "filename": "hum",
             "tags": ["background", "hum"], "duration": 10.0, "is_loopable": True},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        assert len(r.search("door")) >= 1
        assert len(r.search("hum")) >= 1


def test_search_case_insensitive():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "doors/door.mp3", "category": "doors", "filename": "door",
             "tags": ["door"], "duration": 1.5, "is_loopable": False},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        assert len(r.search("DOOR")) >= 1
        assert len(r.search("Door")) >= 1


def test_search_no_match_returns_empty():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "doors/door.mp3", "category": "doors", "filename": "door",
             "tags": ["door"], "duration": 1.5, "is_loopable": False},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        assert r.search("xyzzy") == []


def test_get_ambience_matches_location():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "background/tng_bridge_1.mp3", "category": "background",
             "filename": "tng_bridge_1", "tags": ["background", "bridge"],
             "duration": 60.0, "is_loopable": True},
            {"path": "background/voy_bridge.mp3", "category": "background",
             "filename": "voy_bridge", "tags": ["background", "voy", "bridge"],
             "duration": 60.0, "is_loopable": True},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        amb = r.get_ambience("VOY Bridge")
        assert amb is not None
        assert "voy_bridge" in amb.path


def test_get_ambience_returns_none_for_empty():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "doors/door.mp3", "category": "doors", "filename": "door",
             "tags": ["door"], "duration": 1.5, "is_loopable": False},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        amb = r.get_ambience("Sickbay")
        assert amb is None or not amb.is_loopable


def test_empty_library_no_crash():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        r = SFXRegistry(library_path=str(tmpdir))
        assert r.entries == []
        assert r.search("anything") == []


def test_categories():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        _make_index(tmpdir, [
            {"path": "doors/door.mp3", "category": "doors", "filename": "door",
             "tags": ["door"], "duration": 1.5, "is_loopable": False},
            {"path": "background/hum.mp3", "category": "background", "filename": "hum",
             "tags": ["background"], "duration": 10.0, "is_loopable": True},
        ])
        r = SFXRegistry(library_path=str(tmpdir))
        cats = r.categories()
        assert "doors" in cats
        assert "background" in cats
