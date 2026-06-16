from __future__ import annotations

import re
from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult
from holodeck.agents.video.svg_templates import (
    character_silhouette,
    compose_scene,
    prop_icon,
    scene_background,
    text_overlay,
)
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model


def _parse_scenes(animation_text: str) -> list[dict]:
    scenes = []
    current: dict | None = None
    scene_pattern = re.compile(r"SCENE\s*(\d+):?\s*(.*)", re.IGNORECASE)
    for line in animation_text.split("\n"):
        m = scene_pattern.match(line.strip())
        if m:
            if current:
                scenes.append(current)
            current = {"number": m.group(1), "location": m.group(2).strip(), "lines": []}
        elif current and line.strip():
            current["lines"].append(line.strip())
    if current:
        scenes.append(current)
    if not scenes:
        scenes.append({"number": "1", "location": "unknown", "lines": animation_text.split("\n")})
    return scenes


def _suggest_pose(lines: list[str]) -> str:
    combined = " ".join(lines).lower()
    if any(w in combined for w in ("walk", "run", "enter", "approach", "leave")):
        return "walking"
    return "standing"


_KNOWN_HEADERS = frozenset({
    "CHARACTER", "BODY", "FACE", "HAIR", "COSTUME", "EXPRESSIONS", "SILHOUETTE",
    "HEIGHT", "BUILD", "POSTURE", "EYES", "NOSE", "MOUTH", "SKIN", "AGE",
    "STYLE", "COLOR", "LENGTH", "MATERIALS", "ACCESSORIES",
    "NEUTRAL", "HAPPY", "ANGRY", "FRIGHTENED", "SURPRISED", "SAD",
    "NAME", "ROLE", "GENDER", "SPECIES", "OCCUPATION", "RANK",
    "BACKGROUND", "PERSONALITY", "GOALS", "FLAWS",
})


def _parse_characters(text: str, script: str = "") -> list[str]:
    if script:
        dialogue_names = re.findall(r"^([A-Z][A-Za-z\s]+?):\s*.+$", script, re.MULTILINE)
        dialogue_names = [
            n.strip() for n in dialogue_names
            if n.strip().upper() not in _KNOWN_HEADERS and len(n.strip()) >= 2
        ]
        if dialogue_names:
            return list(dict.fromkeys(dialogue_names))

    names = re.findall(r"CHARACTER:\s*([A-Z][A-Za-z\s]+)", text)
    if names:
        names = [n.strip().rstrip() for n in names if n.strip().rstrip().upper() not in _KNOWN_HEADERS and len(n.strip().rstrip()) >= 2]
    if not names:
        names = re.findall(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s*:", text)
        names = [n.strip() for n in names if n.strip().upper() not in _KNOWN_HEADERS and len(n.strip()) >= 2]
    if not names:
        names = re.findall(r"([A-Z]{2,})", text)
        names = [n.strip() for n in names if n.strip() not in _KNOWN_HEADERS and len(n.strip()) >= 2]
    if not names:
        names = ["Character"]
    return list(dict.fromkeys(names))


def _build_scene_svg(
    scene_num: str,
    location: str,
    lines: list[str],
    characters: list[str],
) -> str:
    bg = scene_background(location)
    pose = _suggest_pose(lines)
    char_svgs = []
    for i, name in enumerate(characters[:4]):
        x = 200 + i * 280
        y = 400 + (i // 2) * 60
        char_svgs.append(character_silhouette(name, x=x, y=y, height=100, pose=pose))

    props = []
    for line in lines:
        l = line.lower()
        if "table" in l or "desk" in l:
            props.append(prop_icon("table", x=640, y=520, size=40))
        if "screen" in l or "monitor" in l or "console" in l or "display" in l:
            props.append(prop_icon("screen", x=960, y=380, size=40))

    overlays = [
        text_overlay(f"Scene {scene_num}: {location}", y=35, size=22),
        text_overlay(f"\"{lines[0][:60] if lines else ''}\"", y=680, size=14),
    ]
    return compose_scene(bg, char_svgs, props, overlays)


class FrameRendererAgent:
    stage = StageType.ANIMATION
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Frame Renderer",
                role="You receive storyboard and animation descriptions and output B&W SVG frame compositions. You translate scene text into visual frame layouts.",
                instructions=[
                    "Parse animation descriptions for scene structure.",
                    "Map characters and props to visual positions.",
                    "Output structured SVG frame descriptions.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("animation") and not context.get("storyboard"):
            return ValidationResult(valid=False, errors=["Animation or storyboard required"])
        return ValidationResult(valid=True)

    @observe(name="frame_renderer.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        animation = context.get("animation", "")
        storyboard = context.get("storyboard", "")
        characters_text = context.get("character_designs", "")
        character_visuals: dict = context.get("character_visuals", {})

        scenes = _parse_scenes(animation or storyboard)
        char_names = _parse_characters(characters_text, script)

        dialogue_pattern = re.compile(r"^[>\s]*\*{0,2}([A-Z][A-Za-z\s]+?)\*{0,2}\s*:\s*(.+)$", re.MULTILINE)
        dialogue_lines = dialogue_pattern.findall(script)
        if not dialogue_lines:
            dialogue_lines = [("Narrator", script[:100])]

        svg_scenes = []
        subtitle_data = []
        sub_frames_n = int(context.get("sub_frames", 6))
        sub_frame_offsets = {
            0: (0, 0, 0),
            1: (12, -6, -5),
            2: (-10, 8, 5),
            3: (16, 0, -8),
            4: (-14, -4, 8),
            5: (8, -10, 0),
        }
        lip_sync_enabled = False
        for i, (speaker, dialogue_text) in enumerate(dialogue_lines[:30]):
            scene = scenes[i % max(len(scenes), 1)]
            location = scene.get("location", "unknown") if scenes else "unknown"
            lines = scene.get("lines", []) if scenes else []

            speaker_upper = speaker.strip().upper()
            speaker_idx = -1
            for j, name in enumerate(char_names):
                if name.strip().upper().startswith(speaker_upper[:6]):
                    speaker_idx = j
                    break
            if speaker_idx < 0:
                speaker_idx = i % max(len(char_names), 1)

            bg = scene_background(location, depth=context.get("background_depth", 1))
            pose = _suggest_pose(lines)
            active_char = char_names[speaker_idx] if speaker_idx < len(char_names) else "Speaker"

            # Visual params from character_visuals
            def _get_visual(char_name: str) -> dict:
                return character_visuals.get(char_name, {})

            props = []
            for line in lines:
                l = line.lower()
                if "table" in l or "desk" in l:
                    props.append(prop_icon("table", x=640, y=520, size=40))
                if "screen" in l or "monitor" in l or "console" in l or "display" in l:
                    props.append(prop_icon("screen", x=960, y=380, size=40))

            overlays = [
                text_overlay(f"{location} — {active_char}", y=35, size=22),
            ]

            n_local = max(min(sub_frames_n, 8), 1)
            for sub_idx in range(n_local):
                dx, dy, dh = sub_frame_offsets.get(sub_idx, (0, 0, 0))
                h_local = 130 + dh

                # Lip sync: toggle mouth every 4-6 frames within this dialogue line
                mouth_open = False
                if sub_frames_n >= 4:
                    toggle_cycle = max(min(sub_frames_n // 2, 6), 4)
                    mouth_open = ((sub_idx // toggle_cycle) % 2) == 0
                    if mouth_open:
                        lip_sync_enabled = True

                char_svgs = []
                for j, name in enumerate(char_names[:2]):
                    v = _get_visual(name)
                    if j == speaker_idx:
                        char_svgs.append(character_silhouette(
                            name, x=640 + dx, y=360 + dy, height=h_local, pose=pose,
                            mouth_open=mouth_open,
                            clothing=v.get("clothing", "uniform"),
                            build=v.get("build", "average"),
                            hair_style=v.get("hair_style", "short"),
                            accessory=v.get("accessory", "none"),
                        ))
                    else:
                        # Listener at side, smaller
                        side_x = 200 if speaker_idx == 0 else 1080
                        char_svgs.append(character_silhouette(
                            name, x=side_x, y=420, height=90, pose=pose,
                            mouth_open=False,
                            clothing=v.get("clothing", "uniform"),
                            build=v.get("build", "average"),
                            hair_style=v.get("hair_style", "short"),
                            accessory=v.get("accessory", "none"),
                        ))
                svg = compose_scene(bg, char_svgs, props, overlays)
                svg_scenes.append(svg)

            subtitle_data.append({
                "frame_index": i * n_local,
                "frame_count": n_local,
                "dialogue_text": dialogue_text,
                "character": active_char,
                "scene": scene.get("number", "1"),
                "location": location,
            })

        context["subtitle_data"] = subtitle_data
        context["frame_layouts"] = [{
            "scene": sd["scene"],
            "character": sd["character"],
            "frame_index": sd["frame_index"],
        } for sd in subtitle_data]
        animation_subframes = int(context.get("sub_frames", 3))
        output = f"FRAMES: {len(svg_scenes)}\n\n" + "\n---NEXT FRAME---\n".join(svg_scenes)
        return AgentOutput(content=output, metadata={
            "stage": "animation", "agent": "frame_renderer",
            "frame_count": len(svg_scenes),
            "subtitle_data": subtitle_data,
            "animation_subframes": animation_subframes,
            "characters_per_frame": min(len(char_names), 2),
            "lip_sync_enabled": lip_sync_enabled,
            "background_depth": context.get("background_depth", 1),
        })

    @observe(name="frame_renderer.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        fc = 0
        if output.metadata:
            fc = output.metadata.get("frame_count", 0)
        if fc == 0:
            return ReviewResult(approved=False, score=0, feedback="No frames generated.")
        return ReviewResult(approved=fc >= 1, score=min(fc * 10, 100), feedback=f"{fc} frames generated.")
