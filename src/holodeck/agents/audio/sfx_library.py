from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SFXEntry:
    path: str
    category: str
    filename: str
    tags: list[str]
    duration: float
    is_loopable: bool


class SFXRegistry:
    def __init__(self, library_path: str = "sfx_library") -> None:
        self.library_path = Path(library_path)
        self.entries: list[SFXEntry] = []
        self._index: dict[str, list[SFXEntry]] = {}
        self.load_index()

    def load_index(self) -> None:
        index_path = self.library_path / "index.json"
        if not index_path.exists():
            logger.warning("SFX index not found at %s", index_path)
            return
        with open(index_path) as f:
            raw = json.load(f)
        entries = []
        for item in raw:
            try:
                entries.append(SFXEntry(**item))
            except (TypeError, KeyError) as exc:
                logger.warning("Skipping invalid SFX entry: %s", exc)
        self.entries = entries
        self._rebuild_index()
        logger.info("Loaded %d SFX entries from %s", len(entries), index_path)

    def _rebuild_index(self) -> None:
        idx: dict[str, list[SFXEntry]] = {}
        for entry in self.entries:
            for tag in entry.tags:
                key = tag.lower()
                idx.setdefault(key, []).append(entry)
        self._index = idx

    def search(self, keyword: str) -> list[SFXEntry]:
        key = keyword.lower().strip()
        result = []
        seen = set()
        for entry in self.entries:
            if key in entry.filename.lower() and entry.path not in seen:
                result.append(entry)
                seen.add(entry.path)
        if key in self._index:
            for entry in self._index[key]:
                if entry.path not in seen:
                    result.append(entry)
                    seen.add(entry.path)
        for entry in self.entries:
            if key in entry.category.lower() and entry.path not in seen:
                result.append(entry)
                seen.add(entry.path)
            if any(key in t.lower() for t in entry.tags) and entry.path not in seen:
                result.append(entry)
                seen.add(entry.path)
        return result

    def get_by_tag(self, tag: str) -> list[SFXEntry]:
        return self._index.get(tag.lower(), [])

    def get_ambience(self, location: str) -> SFXEntry | None:
        loc_lower = location.lower().replace(" ", "_")
        ambience_entries = [e for e in self.entries if e.is_loopable]
        if not ambience_entries:
            ambience_entries = [e for e in self.entries if e.category == "background"]
        for entry in ambience_entries:
            name = entry.filename.lower()
            if name in loc_lower or loc_lower in name:
                return entry
        for entry in ambience_entries:
            for tag in entry.tags:
                if tag.lower() in loc_lower:
                    return entry
        if ambience_entries:
            return ambience_entries[0]
        return None

    def categories(self) -> list[str]:
        cats: list[str] = []
        seen: set[str] = set()
        for entry in self.entries:
            if entry.category not in seen:
                cats.append(entry.category)
                seen.add(entry.category)
        return sorted(cats)
