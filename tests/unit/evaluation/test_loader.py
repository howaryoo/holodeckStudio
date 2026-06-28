from __future__ import annotations

import json
import pytest
from pathlib import Path

from holodeck.evaluation.loader import GoldenDatasetValidationError, load_golden_dataset


VALID_ENTRY = {
    "prompt_id": "test-entry-001",
    "user_prompt": "Monica discovers a rival chef is opening next door.",
    "quality_guidelines": {
        "narrative_goal": "Monica's competitiveness escalates to chaos before resolving with warmth.",
        "character_arcs": {"Monica": "competitive → self-aware", "Chandler": "avoidant → supportive"},
        "comedy_approach": "Escalating situational comedy driven by Monica's competitiveness",
        "emotional_beats": ["Monica's excitement", "Chandler's exasperation", "Resolution with warmth"],
        "production_constraints": ["Max 2 sets", "No more than 2 guest characters"],
        "thematic_focus": "Competitiveness vs self-acceptance",
    },
    "scope_boundaries": {
        "must_include": ["Monica in kitchen context", "Chandler sarcastic comment"],
        "must_exclude": ["Ross dinosaur subplot"],
        "character_focus": ["Monica", "Chandler"],
    },
    "acceptable_variations": ["Rival can be male or female", "Joey may appear for comic relief"],
}


def make_valid_dataset(entries: list[dict] | None = None) -> dict:
    return {
        "version": "1.0",
        "show": "Friends",
        "entries": entries if entries is not None else [VALID_ENTRY],
    }


def write_dataset(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestLoadGoldenDataset:
    def test_loads_valid_single_entry(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path, make_valid_dataset())
        entries = load_golden_dataset(path)
        assert len(entries) == 1
        assert entries[0].prompt_id == "test-entry-001"

    def test_loads_multiple_entries(self, tmp_path: Path) -> None:
        entry2 = {**VALID_ENTRY, "prompt_id": "test-entry-002"}
        path = write_dataset(tmp_path, make_valid_dataset([VALID_ENTRY, entry2]))
        entries = load_golden_dataset(path)
        assert len(entries) == 2

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(GoldenDatasetValidationError, match="Cannot read"):
            load_golden_dataset(tmp_path / "nonexistent.json")

    def test_raises_on_malformed_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{ not valid json }", encoding="utf-8")
        with pytest.raises(GoldenDatasetValidationError, match="Invalid JSON"):
            load_golden_dataset(path)

    def test_raises_on_empty_entries(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path, make_valid_dataset([]))
        with pytest.raises(GoldenDatasetValidationError, match="non-empty"):
            load_golden_dataset(path)

    def test_raises_on_missing_entries_key(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path, {"version": "1.0"})
        with pytest.raises(GoldenDatasetValidationError, match="non-empty"):
            load_golden_dataset(path)

    def test_raises_on_duplicate_prompt_ids(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path, make_valid_dataset([VALID_ENTRY, VALID_ENTRY]))
        with pytest.raises(GoldenDatasetValidationError, match="Duplicate prompt_id"):
            load_golden_dataset(path)

    def test_raises_on_missing_required_field(self, tmp_path: Path) -> None:
        bad_entry = {k: v for k, v in VALID_ENTRY.items() if k != "user_prompt"}
        path = write_dataset(tmp_path, make_valid_dataset([bad_entry]))
        with pytest.raises(GoldenDatasetValidationError, match="user_prompt"):
            load_golden_dataset(path)

    def test_raises_on_non_object_entry(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path, make_valid_dataset(["not-an-object"]))
        with pytest.raises(GoldenDatasetValidationError, match="JSON object"):
            load_golden_dataset(path)

    def test_entry_index_in_error_message(self, tmp_path: Path) -> None:
        bad_entry = {**VALID_ENTRY, "prompt_id": "second", "user_prompt": 123}
        path = write_dataset(tmp_path, make_valid_dataset([VALID_ENTRY, bad_entry]))
        with pytest.raises(GoldenDatasetValidationError, match="index 1"):
            load_golden_dataset(path)
