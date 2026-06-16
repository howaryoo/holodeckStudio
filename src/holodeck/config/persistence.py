from __future__ import annotations

import json
from pathlib import Path

HOLODECK_DIR = Path.home() / ".holodeck"
CONFIG_FILE = HOLODECK_DIR / "config.json"


def _ensure_dir() -> None:
    HOLODECK_DIR.mkdir(parents=True, exist_ok=True)


def load_overrides() -> dict[str, str]:
    _ensure_dir()
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_override(key: str, value: str) -> dict[str, str]:
    overrides = load_overrides()
    overrides[key] = value
    _ensure_dir()
    CONFIG_FILE.write_text(json.dumps(overrides, indent=2))
    return overrides


def clear_overrides() -> None:
    _ensure_dir()
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def get_all_overrides() -> dict[str, str]:
    return load_overrides()
