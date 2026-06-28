from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from holodeck.agents.audio.sfx_library import SFXRegistry

logger = logging.getLogger(__name__)

SCENE_BLOCK_RE = re.compile(
    r"SCENE\s+(\d+)\s*:\s*(.+?)(?=SCENE\s+\d+\s*:|\Z)",
    re.DOTALL | re.IGNORECASE,
)
AMBIENCE_RE = re.compile(r"-\s*AMBIENCE\s*:\s*(.+)", re.IGNORECASE)
FOLEY_RE = re.compile(r"-\s*FOLEY\s*:\s*(.+)", re.IGNORECASE)
SFX_LINE_RE = re.compile(r"-\s*SFX\s*:\s*(.+)", re.IGNORECASE)

STOP_WORDS = {
    "background", "quiet", "ambient", "sound", "noise",
    "soft", "gentle", "low", "constant", "steady",
}


@dataclass
class SceneCue:
    scene_number: int
    location: str
    ambience: str
    foley: str
    sfx: list[str] = field(default_factory=list)


@dataclass
class MatchedScene:
    scene_number: int
    location: str
    ambience_path: str | None = None
    foley_paths: list[str] = field(default_factory=list)
    sfx_paths: list[str] = field(default_factory=list)


class SFXMatcher:
    def __init__(self, registry: SFXRegistry) -> None:
        self.registry = registry
        self._library_root = registry.library_path.resolve()

    def _resolve(self, rel_path: str | None) -> str | None:
        if not rel_path:
            return None
        resolved = self._library_root / rel_path
        return str(resolved) if resolved.exists() else None

    def parse_sound_design(self, text: str) -> list[SceneCue]:
        if not text or not text.strip():
            return []
        cues = []
        for match in SCENE_BLOCK_RE.finditer(text):
            scene_num = int(match.group(1))
            location = match.group(2).strip().split("\n")[0].strip()
            block = match.group(2)
            ambience_match = AMBIENCE_RE.search(block)
            foley_match = FOLEY_RE.search(block)
            sfx_match = SFX_LINE_RE.search(block)
            sfx_items = []
            if sfx_match:
                raw = sfx_match.group(1)
                sfx_items = [s.strip() for s in raw.split(",") if s.strip()]
            cues.append(SceneCue(
                scene_number=scene_num,
                location=location,
                ambience=ambience_match.group(1).strip() if ambience_match else "",
                foley=foley_match.group(1).strip() if foley_match else "",
                sfx=sfx_items,
            ))
        return cues

    def _extract_keywords(self, text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return [w for w in words if w not in STOP_WORDS and len(w) > 2]

    def _match_cue(self, description: str) -> str | None:
        if not description:
            return None
        keywords = self._extract_keywords(description)
        for kw in keywords:
            matches = self.registry.search(kw)
            if matches:
                return matches[0].path
        return None

    def _match_multi(self, descriptions: list[str]) -> list[str]:
        paths = []
        for desc in descriptions:
            path = self._match_cue(desc)
            if path:
                paths.append(path)
        return paths

    def match_cues(self, scene_cues: list[SceneCue]) -> list[MatchedScene]:
        matched = []
        for cue in scene_cues:
            ambience_entry = self.registry.get_ambience(cue.location)
            if ambience_entry:
                ambience_path_resolved = self._resolve(ambience_entry.path)
            else:
                ambience_match = self._match_cue(cue.ambience)
                ambience_path_resolved = self._resolve(ambience_match)

            foley_keywords = self._extract_keywords(cue.foley)
            foley_matches = [self._resolve(m) for m in self._match_multi(foley_keywords)]
            foley_paths = [p for p in foley_matches if p]

            sfx_matches = self._match_multi(cue.sfx)
            sfx_paths = [p for p in [self._resolve(m) for m in sfx_matches] if p]

            matched.append(MatchedScene(
                scene_number=cue.scene_number,
                location=cue.location,
                ambience_path=ambience_path_resolved,
                foley_paths=foley_paths,
                sfx_paths=sfx_paths,
            ))
        return matched
