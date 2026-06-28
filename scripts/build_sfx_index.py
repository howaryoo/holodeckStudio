#!/usr/bin/env python3
"""Build sfx_library/index.json from downloaded MP3 files."""
import json
import subprocess
import sys
from pathlib import Path


def get_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
        return 0.0


def auto_tags(category: str, filename: str) -> list[str]:
    tags = []
    tags.append(category)
    name = filename.lower().replace(".mp3", "")
    parts = name.replace("_", " ").replace("-", " ").split()
    for p in parts:
        if p not in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"):
            tags.append(p)
    return tags


LOOPABLE_CATEGORIES = {"background", "computer"}

MANUAL_LOOPABLE = {
    "tng_bridge_1", "tng_bridge_2", "tng_bridge_3",
    "tng_engineering_hum", "tng_engine_1", "tng_engine_2", "tng_engine_3",
    "tng_hum_clean", "tng_lab", "tng_sickbay", "tng_sickbay_2",
    "tng_cargobay", "tng_jeffreystube", "tng_data_room",
    "voy_bridge", "voy_engineering", "voy_astrometrics",
    "voy_core_1", "voy_core_2", "voy_core_3", "voy_core_4",
    "ds9_infirmary",
    "borg_engine_hum",
    "engineering_clean", "ambient_bridge_1", "computer_sounds",
}


def main():
    sfx_dir = Path(__file__).resolve().parent.parent / "sfx_library"
    if not sfx_dir.exists():
        print(f"SFX library not found at {sfx_dir}", file=sys.stderr)
        sys.exit(1)

    entries = []
    for mp3 in sorted(sfx_dir.rglob("*.mp3")):
        rel = mp3.relative_to(sfx_dir)
        category = rel.parent.name
        filename = mp3.stem
        duration = get_duration(mp3)
        tags = auto_tags(category, filename)
        is_loopable = (category in LOOPABLE_CATEGORIES) or (filename in MANUAL_LOOPABLE)
        entries.append({
            "path": str(rel),
            "category": category,
            "filename": filename,
            "tags": tags,
            "duration": round(duration, 2),
            "is_loopable": is_loopable,
        })

    index_path = sfx_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(entries, f, indent=2)

    print(f"Indexed {len(entries)} files → {index_path}")


if __name__ == "__main__":
    main()
