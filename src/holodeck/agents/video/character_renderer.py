from __future__ import annotations

from math import floor

_BLACK = "#000000"
_WHITE = "#FFFFFF"
_STROKE_W = "3"
_STROKE = f'stroke="{_BLACK}" stroke-width="{_STROKE_W}" stroke-linejoin="round"'

_COMIC_PALETTES: list[dict[str, str]] = [
    {"skin": "#F5D0A9", "uniform": "#CC3333", "hair": "#4A3728", "accent": "#FFD700"},
    {"skin": "#D4A574", "uniform": "#2B5EA7", "hair": "#1A1A1A", "accent": "#C0C0C0"},
    {"skin": "#F0C8A0", "uniform": "#2D7D46", "hair": "#8B4513", "accent": "#DAA520"},
    {"skin": "#E8C39E", "uniform": "#6B3FA0", "hair": "#2F1B0E", "accent": "#E6E6FA"},
    {"skin": "#DDB88A", "uniform": "#C17817", "hair": "#3D2B1F", "accent": "#FF8C00"},
    {"skin": "#F2D5B5", "uniform": "#8B0000", "hair": "#0A0A0A", "accent": "#FF4444"},
    {"skin": "#C9A078", "uniform": "#1C3F60", "hair": "#5C3317", "accent": "#87CEEB"},
    {"skin": "#EED4B8", "uniform": "#4A4A4A", "hair": "#6B3A2A", "accent": "#FF69B4"},
]


def _pick_palette(name: str) -> dict[str, str]:
    idx = abs(hash(name)) % len(_COMIC_PALETTES)
    return _COMIC_PALETTES[idx]


def render_face(
    cx: int, cy: int, head_r: int, mouth_open: bool = False,
    palette: dict[str, str] | None = None,
) -> str:
    if palette is None:
        return _render_face_bw(cx, cy, head_r, mouth_open)
    return _render_face_color(cx, cy, head_r, mouth_open, palette)


def _render_face_color(
    cx: int, cy: int, head_r: int, mouth_open: bool,
    palette: dict[str, str],
) -> str:
    eye_y = cy - floor(head_r * 0.25)
    eye_offset = floor(head_r * 0.3)
    eye_r = max(floor(head_r * 0.1), 2)

    # Head fill (under hair)
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{head_r}" fill="{palette["skin"]}" '
        f'stroke="{_BLACK}" stroke-width="{_STROKE_W}"/>'
    ]

    # Eyes — white with black pupil
    for ex in (cx - eye_offset, cx + eye_offset):
        parts.append(
            f'<circle cx="{ex}" cy="{eye_y}" r="{eye_r + 1}" fill="{_WHITE}" {_STROKE}/>'
        )
        parts.append(
            f'<circle cx="{ex}" cy="{eye_y}" r="{eye_r}" fill="{_BLACK}"/>'
        )

    # Eyebrows
    brow_y = eye_y - eye_r - 3
    brow_w = max(eye_r + 2, 4)
    for bx in (cx - eye_offset, cx + eye_offset):
        parts.append(
            f'<line x1="{bx - brow_w}" y1="{brow_y}" x2="{bx + brow_w}" y2="{brow_y}" '
            f'stroke="{palette["hair"]}" stroke-width="2" stroke-linecap="round"/>'
        )

    # Nose
    nose_y = cy + floor(head_r * 0.15)
    parts.append(
        f'<line x1="{cx}" y1="{eye_y + eye_r + 2}" x2="{cx}" y2="{nose_y}" '
        f'stroke="{_BLACK}" stroke-width="2" stroke-linecap="round"/>'
    )

    # Mouth
    mouth_y = cy + floor(head_r * 0.4)
    mouth_w = max(floor(head_r * 0.25), 4)
    if mouth_open:
        parts.append(
            f'<ellipse cx="{cx}" cy="{mouth_y}" rx="{mouth_w // 2}" '
            f'ry="{max(floor(head_r * 0.08), 2)}" fill="{_BLACK}"/>'
        )
    else:
        parts.append(
            f'<line x1="{cx - mouth_w // 2}" y1="{mouth_y}" '
            f'x2="{cx + mouth_w // 2}" y2="{mouth_y}" '
            f'stroke="{_BLACK}" stroke-width="2" stroke-linecap="round"/>'
        )

    return "\n".join(parts)


def _render_face_bw(cx: int, cy: int, head_r: int, mouth_open: bool) -> str:
    eye_y = cy - floor(head_r * 0.2)
    eye_offset = floor(head_r * 0.35)
    eye_r = max(floor(head_r * 0.12), 1)
    parts: list[str] = []

    for ex in (cx - eye_offset, cx + eye_offset):
        parts.append(f'<circle cx="{ex}" cy="{eye_y}" r="{eye_r}" fill="{_BLACK}"/>')

    nose_y = cy + floor(head_r * 0.15)
    parts.append(
        f'<line x1="{cx}" y1="{eye_y + eye_r}" x2="{cx}" y2="{nose_y}" '
        f'stroke="{_BLACK}" stroke-width="1.5"/>'
    )

    mouth_y = cy + floor(head_r * 0.45)
    mouth_w = floor(head_r * 0.3)
    if mouth_open:
        parts.append(
            f'<ellipse cx="{cx}" cy="{mouth_y}" rx="{mouth_w // 2}" '
            f'ry="{floor(head_r * 0.1)}" '
            f'fill="{_BLACK}" stroke="{_BLACK}" stroke-width="1"/>'
        )
    else:
        parts.append(
            f'<line x1="{cx - mouth_w // 2}" y1="{mouth_y}" '
            f'x2="{cx + mouth_w // 2}" y2="{mouth_y}" '
            f'stroke="{_BLACK}" stroke-width="1.5"/>'
        )

    return "\n".join(parts)


def render_clothing(
    cx: int,
    body_top: int,
    torso_w: int,
    torso_h: int,
    clothing: str = "uniform",
    build: str = "average",
    palette: dict[str, str] | None = None,
) -> str:
    if palette is None:
        return _render_clothing_bw(cx, body_top, torso_w, torso_h, clothing, build)
    return _render_clothing_color(cx, body_top, torso_w, torso_h, clothing, build, palette)


def _render_clothing_color(
    cx: int, body_top: int, torso_w: int, torso_h: int,
    clothing: str, build: str, palette: dict[str, str],
) -> str:
    half = torso_w // 2
    shoulder_w = max(half + 6, half + 4)
    body_bottom = body_top + torso_h
    neckline_y = body_top + floor(torso_h * 0.05)
    uni_color = palette["uniform"]
    accent = palette["accent"]

    if clothing == "civilian":
        neck_r = floor(torso_w * 0.15)
        points = (
            f"{cx - shoulder_w},{body_top} "
            f"{cx - half},{neckline_y + neck_r} "
            f"{cx - half},{body_bottom} "
            f"{cx + half},{body_bottom} "
            f"{cx + half},{neckline_y + neck_r} "
            f"{cx + shoulder_w},{body_top}"
        )
        return (
            f'<polygon points="{points}" fill="{uni_color}" {_STROKE}/>'
        )

    if clothing == "formal":
        points = (
            f"{cx - shoulder_w},{body_top} "
            f"{cx - half},{body_top + 4} "
            f"{cx - half},{body_bottom} "
            f"{cx + half},{body_bottom} "
            f"{cx + half},{body_top + 4} "
            f"{cx + shoulder_w},{body_top}"
        )
        tie_top = neckline_y
        tie_bot = body_top + floor(torso_h * 0.4)
        tie_w = max(floor(torso_w * 0.12), 2)
        return (
            f'<polygon points="{points}" fill="{uni_color}" {_STROKE}/>'
            f'\n<polygon points="{cx - tie_w},{tie_top} {cx + tie_w},{tie_top} '
            f'{cx + tie_w // 2},{tie_bot} {cx},{tie_bot + 4} {cx - tie_w // 2},{tie_bot}" '
            f'fill="{accent}" {_STROKE}/>'
        )

    if clothing == "cloak":
        points = (
            f"{cx - shoulder_w - 8},{body_top - 2} "
            f"{cx - half - 4},{body_top + floor(torso_h * 0.1)} "
            f"{cx - half - 6},{body_bottom + 8} "
            f"{cx + half + 6},{body_bottom + 8} "
            f"{cx + half + 4},{body_top + floor(torso_h * 0.1)} "
            f"{cx + shoulder_w + 8},{body_top - 2}"
        )
        return (
            f'<polygon points="{points}" fill="{uni_color}" {_STROKE}/>'
        )

    # Uniform (default)
    torso_rect = (
        f'<rect x="{cx - half}" y="{neckline_y}" width="{torso_w}" '
        f'height="{body_bottom - neckline_y}" fill="{uni_color}" {_STROKE}/>'
    )
    collar_points = (
        f"{cx - shoulder_w},{body_top} "
        f"{cx - half},{neckline_y} {cx},{neckline_y + 2} "
        f"{cx + half},{neckline_y} "
        f"{cx + shoulder_w},{body_top}"
    )
    collar = (
        f'\n<polygon points="{collar_points}" fill="{accent}" {_STROKE}/>'
    )
    stripe_y1 = neckline_y + 2
    stripe_y2 = neckline_y + floor(torso_h * 0.1)
    stripes = (
        f'\n<line x1="{cx - shoulder_w + 2}" y1="{stripe_y1}" '
        f'x2="{cx - half + 2}" y2="{stripe_y2}" '
        f'stroke="{accent}" stroke-width="2" stroke-linecap="round"/>'
        f'\n<line x1="{cx + shoulder_w - 2}" y1="{stripe_y1}" '
        f'x2="{cx + half - 2}" y2="{stripe_y2}" '
        f'stroke="{accent}" stroke-width="2" stroke-linecap="round"/>'
    )
    return torso_rect + collar + stripes


def _render_clothing_bw(
    cx: int, body_top: int, torso_w: int, torso_h: int,
    clothing: str, build: str,
) -> str:
    half = torso_w // 2
    shoulder_w = max(half + 4, half + 2)
    body_bottom = body_top + torso_h
    neckline_y = body_top + floor(torso_h * 0.05)
    _s = f'fill="{_WHITE}" stroke="{_BLACK}" stroke-width="2"'

    if clothing == "civilian":
        neck_r = floor(torso_w * 0.15)
        points = (
            f"{cx - shoulder_w},{body_top} "
            f"{cx - half},{neckline_y + neck_r} "
            f"{cx - half},{body_bottom} {cx + half},{body_bottom} "
            f"{cx + half},{neckline_y + neck_r} "
            f"{cx + shoulder_w},{body_top}"
        )
        return f'<polygon points="{points}" {_s}/>'

    if clothing == "formal":
        points = (
            f"{cx - shoulder_w},{body_top} "
            f"{cx - half},{body_top + 4} "
            f"{cx - half},{body_bottom} {cx + half},{body_bottom} "
            f"{cx + half},{body_top + 4} "
            f"{cx + shoulder_w},{body_top}"
        )
        tie_top = neckline_y
        tie_bot = body_top + floor(torso_h * 0.4)
        tie_w = max(floor(torso_w * 0.12), 2)
        return (
            f'<polygon points="{points}" {_s}/>'
            f'\n<polygon points="{cx - tie_w},{tie_top} {cx + tie_w},{tie_top} '
            f'{cx + tie_w // 2},{tie_bot} {cx},{tie_bot + 4} {cx - tie_w // 2},{tie_bot}" '
            f'fill="{_BLACK}"/>'
        )

    if clothing == "cloak":
        points = (
            f"{cx - shoulder_w - 8},{body_top - 2} "
            f"{cx - half - 4},{body_top + floor(torso_h * 0.1)} "
            f"{cx - half - 6},{body_bottom + 8} "
            f"{cx + half + 6},{body_bottom + 8} "
            f"{cx + half + 4},{body_top + floor(torso_h * 0.1)} "
            f"{cx + shoulder_w + 8},{body_top - 2}"
        )
        return f'<polygon points="{points}" {_s}/>'

    # Uniform (default)
    torso_rect = (
        f'<rect x="{cx - half}" y="{neckline_y}" '
        f'width="{torso_w}" height="{body_bottom - neckline_y}" {_s}/>'
    )
    collar_points = (
        f"{cx - shoulder_w},{body_top} "
        f"{cx - half},{neckline_y} {cx},{neckline_y} "
        f"{cx + half},{neckline_y} "
        f"{cx + shoulder_w},{body_top}"
    )
    collar = f'<polygon points="{collar_points}" {_s}/>'
    stripe_y1 = neckline_y + 2
    stripe_y2 = neckline_y + floor(torso_h * 0.1)
    stripes = (
        f'\n<line x1="{cx - shoulder_w + 2}" y1="{stripe_y1}" '
        f'x2="{cx - half + 2}" y2="{stripe_y2}" '
        f'stroke="{_BLACK}" stroke-width="1.5"/>'
        f'\n<line x1="{cx + shoulder_w - 2}" y1="{stripe_y1}" '
        f'x2="{cx + half - 2}" y2="{stripe_y2}" '
        f'stroke="{_BLACK}" stroke-width="1.5"/>'
    )
    return torso_rect + collar + stripes


def render_hair(
    cx: int, cy: int, head_r: int, hair_style: str = "short",
    palette: dict[str, str] | None = None,
) -> str:
    if palette is None:
        hair_color = _BLACK
        opacity = "0.85"
    else:
        hair_color = palette["hair"]
        opacity = "1"

    if hair_style == "bald":
        return ""

    top_y = cy - head_r
    left_x = cx - head_r
    right_x = cx + head_r

    if hair_style == "long":
        return (
            f'<path d="M {left_x},{cy} '
            f'Q {cx - head_r - 2},{top_y - head_r // 2} {cx},{top_y - head_r // 2} '
            f'Q {cx + head_r + 2},{top_y - head_r // 2} {right_x},{cy} '
            f'Q {right_x + 2},{cy + head_r} {right_x + 4},{cy + head_r + head_r // 2} '
            f'Q {cx + 2},{cy + head_r + 6} {cx - 4},{cy + head_r + head_r // 2} '
            f'Q {left_x - 2},{cy + head_r} {left_x},{cy} Z" '
            f'fill="{hair_color}" opacity="{opacity}"/>'
        )

    if hair_style == "curly":
        return (
            f'<path d="M {left_x},{cy} '
            f'Q {cx - head_r - 4},{top_y - 2} {cx},{top_y - head_r // 4} '
            f'Q {cx + head_r + 4},{top_y - 2} {right_x},{cy} Z" '
            f'fill="{hair_color}" opacity="{opacity}"/>'
            f'<circle cx="{cx - head_r // 2}" cy="{top_y + 2}" '
            f'r="{max(head_r // 4, 1)}" fill="{hair_color}" opacity="{opacity}"/>'
            f'<circle cx="{cx + head_r // 2}" cy="{top_y + 2}" '
            f'r="{max(head_r // 4, 1)}" fill="{hair_color}" opacity="{opacity}"/>'
        )

    if hair_style == "ponytail":
        tail_x = cx + head_r + 4
        tail_y = cy + head_r // 2
        return (
            f'<path d="M {left_x},{cy} '
            f'Q {cx - head_r - 2},{top_y - 2} {cx},{top_y - head_r // 4} '
            f'Q {cx + head_r + 2},{top_y - 2} {right_x},{cy} Z" '
            f'fill="{hair_color}" opacity="{opacity}"/>'
            f'\n<path d="M {cx + head_r},{cy} Q {tail_x + 4},{tail_y} '
            f'{tail_x},{tail_y + head_r} Q {tail_x - 4},{tail_y} '
            f'{cx + head_r},{cy} Z" '
            f'fill="{hair_color}" opacity="{opacity}"/>'
        )

    # Short hair (default)
    return (
        f'<path d="M {left_x},{cy} '
        f'Q {cx - head_r - 2},{top_y - 3} {cx},{top_y - head_r // 3} '
        f'Q {cx + head_r + 2},{top_y - 3} {right_x},{cy} Z" '
        f'fill="{hair_color}" opacity="{opacity}"/>'
    )


def render_accessory(
    cx: int, cy: int, head_r: int,
    body_top: int, torso_w: int,
    accessory: str = "none",
    palette: dict[str, str] | None = None,
) -> str:
    if accessory == "none":
        return ""

    if palette is None:
        fill = _BLACK
        stroke = _BLACK
    else:
        fill = palette["accent"]
        stroke = _BLACK

    if accessory == "hat":
        brim_w = head_r + 6
        brim_y = cy - head_r
        return (
            f'<rect x="{cx - brim_w}" y="{brim_y - 3}" width="{brim_w * 2}" height="3" '
            f'fill="{fill}" {_STROKE}/>'
            f'\n<rect x="{cx - head_r // 2}" y="{brim_y - head_r // 2}" '
            f'width="{head_r}" height="{head_r // 2}" fill="{fill}" {_STROKE}/>'
        )

    if accessory == "cape":
        cape_top = body_top - 2
        cape_bot = body_top + floor(head_r * 1.5)
        return (
            f'<path d="M {cx - torso_w - 6},{cape_top} '
            f'Q {cx - torso_w - 10},{cape_bot} {cx},{cape_bot + 4} '
            f'Q {cx + torso_w + 10},{cape_bot} {cx + torso_w + 6},{cape_top} Z" '
            f'fill="{fill}" {_STROKE}/>'
        )

    if accessory == "badge":
        badge_x = cx + torso_w // 4
        badge_y = body_top + floor(head_r * 0.4)
        badge_w = max(floor(torso_w * 0.12), 5)
        badge_h = max(floor(head_r * 0.15), 4)
        return (
            f'<rect x="{badge_x}" y="{badge_y}" width="{badge_w}" height="{badge_h}" '
            f'fill="{fill}" {_STROKE}/>'
        )

    if accessory == "weapon":
        wx = cx + torso_w + 8
        wy = body_top + floor(head_r * 0.3)
        wlen = floor(head_r * 1.2)
        return (
            f'<line x1="{wx}" y1="{wy}" x2="{wx}" y2="{wy + wlen}" '
            f'stroke="{fill}" stroke-width="4" stroke-linecap="round"/>'
            f'\n<line x1="{wx}" y1="{wy}" x2="{wx + 6}" y2="{wy - 4}" '
            f'stroke="{fill}" stroke-width="3" stroke-linecap="round"/>'
        )

    return ""
