from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003

from pydantic import ValidationError

from holodeck.evaluation.schemas import GoldenDatasetEntry


class GoldenDatasetValidationError(ValueError):
    pass


def load_golden_dataset(path: Path) -> list[GoldenDatasetEntry]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise GoldenDatasetValidationError(f"Cannot read golden dataset file: {e}") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GoldenDatasetValidationError(f"Invalid JSON in golden dataset: {e}") from e

    if not isinstance(data, dict):
        raise GoldenDatasetValidationError("Golden dataset must be a JSON object")

    entries_raw = data.get("entries")
    if not isinstance(entries_raw, list) or len(entries_raw) == 0:
        raise GoldenDatasetValidationError("Golden dataset must have a non-empty 'entries' list")

    entries: list[GoldenDatasetEntry] = []
    seen_ids: set[str] = set()

    for i, raw_entry in enumerate(entries_raw):
        try:
            entry = validate_entry(raw_entry)
        except GoldenDatasetValidationError as e:
            raise GoldenDatasetValidationError(f"Entry at index {i}: {e}") from e

        if entry.prompt_id in seen_ids:
            raise GoldenDatasetValidationError(
                f"Duplicate prompt_id '{entry.prompt_id}' at index {i}"
            )
        seen_ids.add(entry.prompt_id)
        entries.append(entry)

    return entries


def validate_entry(raw_entry: object) -> GoldenDatasetEntry:
    if not isinstance(raw_entry, dict):
        raise GoldenDatasetValidationError("Each entry must be a JSON object")

    try:
        return GoldenDatasetEntry.model_validate(raw_entry)
    except ValidationError as e:
        field_errors = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in e.errors()
        )
        raise GoldenDatasetValidationError(f"Validation failed — {field_errors}") from e
