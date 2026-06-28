from __future__ import annotations

from math import floor

SVG_HEADER = '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">'
SVG_FOOTER = "</svg>"

_BLACK = "#000000"
_WHITE = "#FFFFFF"
_GRAY = "#888888"


def _detect_location_props(location: str) -> list[tuple[str, int, int, int]]:
    loc = location.lower()
    found: list[tuple[str, int, int, int]] = []
    if "window" in loc:
        found.append(("window", 1100, 250, 80))
    if "door" in loc:
        found.append(("door", 150, 200, 100))
    if "desk" in loc or "console" in loc:
        found.append(("desk", 640, 500, 50))
    if "table" in loc:
        found.append(("table", 640, 500, 50))
    if "screen" in loc or "monitor" in loc or "display" in loc:
        found.append(("screen", 900, 400, 45))
    if "chair" in loc:
        found.append(("chair", 500, 470, 30))
        found.append(("chair", 780, 470, 30))
    return found


_MOOD_COLORS: dict[str, dict[str, str]] = {
    "warm": {"wall": "#F5E6CA", "floor": "#E8D5B0", "ceiling": "#FFF8E7", "sky": "#FFD4A8"},
    "cool": {"wall": "#D0E0F0", "floor": "#C0D0E0", "ceiling": "#E8F0FF", "sky": "#A0C8E8"},
    "sepia": {"wall": "#E8D8B8", "floor": "#D8C8A8", "ceiling": "#F0E8D0", "sky": "#D4C498"},
    "vivid": {"wall": "#E0E8F0", "floor": "#D0D8E0", "ceiling": "#F0F4FF", "sky": "#88B8E8"},
    "noir": {"wall": "#444444", "floor": "#333333", "ceiling": "#555555", "sky": "#2A2A2A"},
    "neutral": {"wall": "#EEEEEE", "floor": "#DDDDDD", "ceiling": "#F5F5F5", "sky": "#CCCCCC"},
}


def scene_background(
    location: str,
    mood: str = "neutral",
    props: list[str] | None = None,
    depth: int = 1,
) -> str:
    loc_lower = location.lower()
    mc = _MOOD_COLORS.get(mood, _MOOD_COLORS["neutral"])
    wall = mc["wall"]
    floor_c = mc["floor"]
    ceiling = mc["ceiling"]
    sky = mc["sky"]

    bg_parts: list[str] = [
        f'<rect width="1280" height="720" fill="{wall}" stroke="{_BLACK}" stroke-width="3"/>',
    ]

    if depth >= 2:
        if "exterior" in loc_lower or "outside" in loc_lower or "mars" in loc_lower:
            bg_parts.append(
                f'<rect x="0" y="0" width="1280" height="480" fill="{sky}" '
                f'stroke="{_GRAY}" stroke-width="1"/>'
            )
            bg_parts.append(
                f'<line x1="0" y1="100" x2="1280" y2="100" stroke="{_GRAY}" stroke-width="1" opacity="0.2"/>'
            )
        elif "interior" in loc_lower or "inside" in loc_lower or "room" in loc_lower:
            bg_parts.append(
                f'<rect x="0" y="0" width="1280" height="80" fill="{ceiling}" '
                f'stroke="{_GRAY}" stroke-width="1"/>'
            )

    if "interior" in loc_lower or "inside" in loc_lower or "room" in loc_lower:
        bg_parts += [
            f'<line x1="0" y1="80" x2="1280" y2="80" stroke="{_GRAY}" stroke-width="1"/>',
            f'<line x1="0" y1="360" x2="1280" y2="360" stroke="{_BLACK}" stroke-width="2"/>',
            f'<rect x="0" y="360" width="1280" height="360" fill="{floor_c}" stroke="{_BLACK}" stroke-width="1"/>',
            f'<line x1="213" y1="360" x2="213" y2="720" stroke="{_GRAY}" stroke-width="1" opacity="0.3"/>',
            f'<line x1="426" y1="360" x2="426" y2="720" stroke="{_GRAY}" stroke-width="1" opacity="0.3"/>',
            f'<line x1="640" y1="360" x2="640" y2="720" stroke="{_GRAY}" stroke-width="1" opacity="0.3"/>',
            f'<line x1="853" y1="360" x2="853" y2="720" stroke="{_GRAY}" stroke-width="1" opacity="0.3"/>',
            f'<line x1="1066" y1="360" x2="1066" y2="720" stroke="{_GRAY}" stroke-width="1" opacity="0.3"/>',
        ]
    elif "exterior" in loc_lower or "outside" in loc_lower or "mars" in loc_lower:
        bg_parts += [
            f'<line x1="0" y1="480" x2="1280" y2="480" stroke="{_BLACK}" stroke-width="2"/>',
            f'<rect x="0" y="480" width="1280" height="240" fill="{floor_c}" stroke="{_BLACK}" stroke-width="1"/>',
            f'<line x1="0" y1="520" x2="1280" y2="520" stroke="{_GRAY}" stroke-width="1" opacity="0.4"/>',
            f'<line x1="0" y1="580" x2="1280" y2="580" stroke="{_GRAY}" stroke-width="1" opacity="0.4"/>',
            f'<line x1="0" y1="640" x2="1280" y2="640" stroke="{_GRAY}" stroke-width="1" opacity="0.4"/>',
        ]

    if depth >= 3:
        bg_parts.append(
            f'<ellipse cx="640" cy="360" rx="700" ry="400" fill="none" '
            f'stroke="{_BLACK}" stroke-width="120" opacity="0.08"/>'
        )
        bg_parts.append(
            f'<rect x="0" y="0" width="10" height="720" fill="{_BLACK}" opacity="0.3"/>'
        )
        bg_parts.append(
            f'<rect x="1270" y="0" width="10" height="720" fill="{_BLACK}" opacity="0.3"/>'
        )

    bg_parts += [
        f'<rect x="0" y="0" width="1280" height="8" fill="{_BLACK}"/>',
        f'<rect x="0" y="712" width="1280" height="8" fill="{_BLACK}"/>',
    ]

    detected = _detect_location_props(location)
    for shape, px, py, psize in detected:
        bg_parts.append(prop_icon(shape, px, py, psize, mood=mood))

    if props:
        for kw in props:
            kw_lower = kw.lower()
            kw_shapes = _detect_location_props(kw_lower)
            if not kw_shapes:
                kw_shapes = [(kw_lower, 640, 500, 40)]
            for shape, px, py, psize in kw_shapes:
                bg_parts.append(prop_icon(shape, px, py, psize, mood=mood))

    return "\n".join(bg_parts)


def character_silhouette(
    name: str,
    x: int = 640,
    y: int = 360,
    height: int = 120,
    pose: str = "standing",
    mouth_open: bool = False,
    clothing: str = "uniform",
    build: str = "average",
    hair_style: str = "short",
    accessory: str = "none",
    palette: dict[str, str] | None = None,
) -> str:
    from holodeck.agents.video.character_renderer import (
        _pick_palette,
        render_accessory,
        render_clothing,
        render_face,
        render_hair,
    )

    if palette is None:
        palette = _pick_palette(name)

    head_r = floor(height * 0.15)
    torso_h = floor(height * 0.35)
    leg_h = floor(height * 0.3)
    thigh_h = floor(leg_h * 0.5)
    cx, cy = x, y - floor(height * 0.5) - head_r
    body_top = cy + head_r
    body_bottom = body_top + torso_h
    arm_h = floor(torso_h * 0.7)

    if build == "slim":
        torso_w = floor(height * 0.16)
    elif build == "athletic":
        torso_w = floor(height * 0.22)
    elif build == "heavy":
        torso_w = floor(height * 0.26)
    else:
        torso_w = floor(height * 0.2)

    parts: list[str] = []

    # Torso (clothing-aware)
    parts.append(render_clothing(cx, body_top, torso_w, torso_h, clothing, build, palette))

    # Arms — shoulder to elbow
    shoulder_y = body_top + floor(torso_h * 0.1)
    elbow_y = shoulder_y + arm_h
    arm_inset = floor(torso_w * 0.25)
    _as = f'stroke="{_BLACK}" stroke-width="2" stroke-linecap="round"'
    if pose == "walking":
        parts.append(f'<line x1="{cx - arm_inset}" y1="{shoulder_y}" x2="{cx - torso_w}" y2="{elbow_y}" {_as}/>')
        parts.append(f'<line x1="{cx + arm_inset}" y1="{shoulder_y}" x2="{cx + torso_w}" y2="{elbow_y}" {_as}/>')
        parts.append(f'<line x1="{cx - torso_w}" y1="{elbow_y}" x2="{cx - torso_w - 5}" y2="{elbow_y + arm_h}" {_as}/>')
        parts.append(f'<line x1="{cx + torso_w}" y1="{elbow_y}" x2="{cx + torso_w + 5}" y2="{elbow_y + arm_h}" {_as}/>')
    else:
        parts.append(f'<line x1="{cx - arm_inset}" y1="{shoulder_y}" x2="{cx - torso_w - 5}" y2="{elbow_y}" {_as}/>')
        parts.append(f'<line x1="{cx + arm_inset}" y1="{shoulder_y}" x2="{cx + torso_w + 5}" y2="{elbow_y}" {_as}/>')
        parts.append(f'<line x1="{cx - torso_w - 5}" y1="{elbow_y}" x2="{cx - torso_w - 5}" y2="{elbow_y + arm_h}" {_as}/>')
        parts.append(f'<line x1="{cx + torso_w + 5}" y1="{elbow_y}" x2="{cx + torso_w + 5}" y2="{elbow_y + arm_h}" {_as}/>')

    # Legs
    if pose == "walking":
        parts.append(f'<line x1="{cx}" y1="{body_bottom}" x2="{cx - 12}" y2="{body_bottom + thigh_h}" {_as}/>')
        parts.append(f'<line x1="{cx - 12}" y1="{body_bottom + thigh_h}" x2="{cx - 18}" y2="{body_bottom + leg_h}" {_as}/>')
        parts.append(f'<line x1="{cx}" y1="{body_bottom}" x2="{cx + 12}" y2="{body_bottom + thigh_h}" {_as}/>')
        parts.append(f'<line x1="{cx + 12}" y1="{body_bottom + thigh_h}" x2="{cx + 18}" y2="{body_bottom + leg_h}" {_as}/>')
    else:
        parts.append(f'<line x1="{cx}" y1="{body_bottom}" x2="{cx - 6}" y2="{body_bottom + thigh_h}" {_as}/>')
        parts.append(f'<line x1="{cx - 6}" y1="{body_bottom + thigh_h}" x2="{cx - 8}" y2="{body_bottom + leg_h}" {_as}/>')
        parts.append(f'<line x1="{cx}" y1="{body_bottom}" x2="{cx + 6}" y2="{body_bottom + thigh_h}" {_as}/>')
        parts.append(f'<line x1="{cx + 6}" y1="{body_bottom + thigh_h}" x2="{cx + 8}" y2="{body_bottom + leg_h}" {_as}/>')

    # Head — filled with skin color
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{head_r}" '
        f'fill="{palette["skin"]}" stroke="{_BLACK}" stroke-width="3"/>'
    )

    # Face
    parts.append(render_face(cx, cy, head_r, mouth_open, palette))

    # Hair
    parts.append(render_hair(cx, cy, head_r, hair_style, palette))

    # Accessory
    parts.append(render_accessory(cx, cy, head_r, body_top, torso_w, accessory, palette))

    parts.append(
        f'<text x="{cx}" y="{y + floor(height * 0.4)}" text-anchor="middle" '
        f'font-family="DejaVu Sans" font-size="13" font-weight="bold" '
        f'fill="{_BLACK}" stroke="{_WHITE}" stroke-width="0.5">{name}</text>'
    )
    return "\n".join(parts)


_PROP_FILLS: dict[str, str] = {
    "wood": "#C4A46C",
    "metal": "#A0A8B0",
    "screen": "#88CCFF",
    "wall": "#DDDDDD",
}


def prop_icon(shape: str, x: int, y: int, size: int = 30, mood: str = "") -> str:
    h = size // 2
    fill = _PROP_FILLS.get("wood", _WHITE)
    surface = _WHITE
    if shape == "table" or shape == "desk" or shape == "console":
        return (
            f'<rect x="{x - size}" y="{y - h}" width="{size * 2}" height="{h}" '
            f'fill="{_PROP_FILLS["wood"]}" stroke="{_BLACK}" stroke-width="2" rx="2"/>'
            f'<line x1="{x - size + 5}" y1="{y}" x2="{x - size + 5}" y2="{y + size}" '
            f'stroke="{_BLACK}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="{x + size - 5}" y1="{y}" x2="{x + size - 5}" y2="{y + size}" '
            f'stroke="{_BLACK}" stroke-width="3" stroke-linecap="round"/>'
        )
    if shape == "chair":
        return (
            f'<rect x="{x - h}" y="{y - h}" width="{size}" height="{h}" '
            f'fill="{_PROP_FILLS["metal"]}" stroke="{_BLACK}" stroke-width="2" rx="2"/>'
            f'<line x1="{x - h + 4}" y1="{y}" x2="{x - h + 4}" y2="{y + size}" '
            f'stroke="{_BLACK}" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="{x + h - 4}" y1="{y}" x2="{x + h - 4}" y2="{y + size}" '
            f'stroke="{_BLACK}" stroke-width="3" stroke-linecap="round"/>'
        )
    if shape == "screen" or shape == "monitor" or shape == "display":
        return (
            f'<rect x="{x - h}" y="{y - h}" width="{size}" height="{floor(size * 0.75)}" '
            f'fill="{_PROP_FILLS["screen"]}" stroke="{_BLACK}" stroke-width="2" rx="2"/>'
            f'<line x1="{x}" y1="{y + floor(size * 0.75)}" x2="{x}" y2="{y + size}" '
            f'stroke="{_BLACK}" stroke-width="3" stroke-linecap="round"/>'
            f'<rect x="{x - floor(size * 0.15)}" y="{y + floor(size * 0.75)}" '
            f'width="{floor(size * 0.3)}" height="{floor(size * 0.25)}" fill="{_BLACK}" rx="1"/>'
        )
    if shape == "window":
        return (
            f'<rect x="{x - h}" y="{y - size}" width="{size}" height="{size * 2}" '
            f'fill="{_PROP_FILLS["screen"]}" stroke="{_BLACK}" stroke-width="2" rx="2" opacity="0.6"/>'
            f'<line x1="{x}" y1="{y - size}" x2="{x}" y2="{y + size}" stroke="{_BLACK}" stroke-width="2"/>'
            f'<line x1="{x - h}" y1="{y}" x2="{x + h}" y2="{y}" stroke="{_BLACK}" stroke-width="2"/>'
        )
    if shape == "door":
        return (
            f'<rect x="{x - h}" y="{y - size}" width="{size}" height="{size * 2}" '
            f'fill="{_PROP_FILLS["wood"]}" stroke="{_BLACK}" stroke-width="2" rx="2"/>'
            f'<circle cx="{x + h - 6}" cy="{y}" r="3" fill="{_BLACK}"/>'
        )
    return ""


def text_overlay(text: str, x: int = 640, y: int = 40, size: int = 20) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-family="DejaVu Sans" '
        f'font-size="{size}" fill="{_BLACK}" font-weight="bold">{text}</text>'
    )


def compose_scene(
    background: str,
    characters: list[str],
    props: list[str],
    overlays: list[str],
) -> str:
    parts = [SVG_HEADER]
    parts.append(background)
    parts.extend(characters)
    parts.extend(props)
    parts.extend(overlays)
    parts.append(SVG_FOOTER)
    return "\n".join(parts)
