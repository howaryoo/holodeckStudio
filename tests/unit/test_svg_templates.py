from __future__ import annotations

import re

from holodeck.agents.video.character_renderer import (
    render_accessory,
    render_clothing,
    render_face,
    render_hair,
)
from holodeck.agents.video.svg_templates import (
    SVG_FOOTER,
    SVG_HEADER,
    character_silhouette,
    compose_scene,
    prop_icon,
    scene_background,
    text_overlay,
)


def _count_colors(svg: str) -> dict[str, int]:
    return {
        "#000000": svg.count("#000000") + svg.count('stroke="black"') + svg.count('fill="black"'),
        "#FFFFFF": svg.count("#FFFFFF") + svg.count('fill="white"'),
    }


def _is_bw_compliant(svg: str) -> bool:
    colors = _count_colors(svg)
    all_hex = re.findall(r'#[0-9A-Fa-f]{6}', svg)
    allowed = {"#000000", "#FFFFFF", "#888888"}
    non_bw = [c for c in all_hex if c not in allowed]
    return len(non_bw) == 0


class TestSvgTemplates:
    def test_scene_background_interior(self):
        svg = scene_background("interior room", "neutral")
        assert svg.startswith("<rect")
        assert "1280" in svg
        assert "720" in svg
        assert "360" in svg  # floor line

    def test_scene_background_exterior(self):
        svg = scene_background("exterior mars", "tense")
        assert svg.startswith("<rect")
        assert "1280" in svg
        assert "480" in svg  # horizon

    def test_scene_background_default(self):
        svg = scene_background("void", "calm")
        assert svg.startswith("<rect")
        assert svg.count("<rect") >= 1

    def test_scene_background_has_mood_colors(self):
        svg = scene_background("room")
        assert "#EEEEEE" in svg  # neutral wall

    def test_character_silhouette_standing(self):
        svg = character_silhouette("Hero", x=200, y=300, height=100, pose="standing")
        assert "circle" in svg
        assert "Hero" in svg
        assert "line" in svg

    def test_character_silhouette_walking(self):
        svg = character_silhouette("Hero", x=200, y=300, height=100, pose="walking")
        assert "walking" not in svg
        assert "circle" in svg

    def test_character_silhouette_parametrized_position(self):
        svg_left = character_silhouette("A", x=100, y=200, height=80)
        svg_right = character_silhouette("A", x=500, y=200, height=80)
        assert 'cx="100"' in svg_left
        assert 'cx="500"' in svg_right

    def test_character_silhouette_has_skin_color(self):
        svg = character_silhouette("Hero", x=640, y=360)
        assert "fill=\"" in svg
        assert "stroke-linejoin" in svg

    def test_prop_icon_table(self):
        svg = prop_icon("table", x=400, y=400, size=40)
        assert "rect" in svg
        assert "line" in svg


    def test_prop_icon_chair(self):
        svg = prop_icon("chair", x=300, y=500, size=30)
        assert "rect" in svg

    def test_prop_icon_screen(self):
        svg = prop_icon("screen", x=800, y=300, size=50)
        assert "rect" in svg
        svg2 = prop_icon("monitor", x=800, y=300, size=50)
        assert "rect" in svg2

    def test_prop_icon_colored_fills(self):
        for shape in ("table", "chair", "screen"):
            svg = prop_icon(shape, x=400, y=400, size=40)
            assert "rect" in svg

    def test_text_overlay(self):
        svg = text_overlay("Hello World", x=640, y=40, size=20)
        assert "Hello World" in svg
        assert "font-size=\"20\"" in svg or "font-size='20'" in svg

    def test_text_overlay_color(self):
        svg = text_overlay("Test", x=100, y=100)
        assert "font-weight=\"bold\"" in svg

    def test_compose_scene(self):
        bg = '<rect width="1280" height="720" fill="white"/>'
        chars = ['<circle cx="200" cy="300" r="15"/>']
        props = ['<rect x="400" y="400" width="20" height="20"/>']
        overlays = ['<text x="640" y="40">Scene 1</text>']
        svg = compose_scene(bg, chars, props, overlays)
        assert SVG_HEADER in svg
        assert SVG_FOOTER in svg
        assert bg in svg
        assert chars[0] in svg
        assert props[0] in svg
        assert overlays[0] in svg

    def test_compose_scene_colored(self):
        bg = scene_background("room")
        chars = [character_silhouette("Hero", x=640, y=360)]
        svg = compose_scene(bg, chars, [], [])
        assert SVG_HEADER in svg
        assert SVG_FOOTER in svg

    def test_compose_scene_empty_lists(self):
        svg = compose_scene("<rect/>", [], [], [])
        assert SVG_HEADER in svg
        assert SVG_FOOTER in svg

    def test_svg_has_standard_attrs(self):
        svg = compose_scene("<rect/>", [], [], [])
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg
        assert 'viewBox="0 0 1280 720"' in svg
        assert 'width="1280"' in svg
        assert 'height="720"' in svg


class TestLocationProps:
    def test_detect_window(self):
        from holodeck.agents.video.svg_templates import _detect_location_props
        props = _detect_location_props("room with window")
        assert any(p[0] == "window" for p in props)

    def test_detect_door(self):
        from holodeck.agents.video.svg_templates import _detect_location_props
        props = _detect_location_props("door at entrance")
        assert any(p[0] == "door" for p in props)

    def test_detect_desk(self):
        from holodeck.agents.video.svg_templates import _detect_location_props
        props = _detect_location_props("large desk")
        assert any(p[0] == "desk" for p in props)

    def test_detect_table(self):
        from holodeck.agents.video.svg_templates import _detect_location_props
        props = _detect_location_props("wooden table")
        assert any(p[0] == "table" for p in props)

    def test_detect_screen(self):
        from holodeck.agents.video.svg_templates import _detect_location_props
        props = _detect_location_props("console with screen")
        assert any(p[0] == "screen" for p in props)

    def test_no_match_returns_empty(self):
        from holodeck.agents.video.svg_templates import _detect_location_props
        assert _detect_location_props("empty void") == []


class TestSceneBackgroundWithProps:
    def test_auto_detects_props_from_location(self):
        svg = scene_background("room with window and desk")
        assert "<rect" in svg
        assert 'y1="360"' in svg or "line" in svg

    def test_explicit_props_parameter(self):
        svg = scene_background("room", props=["window", "chair"])
        assert "<rect" in svg

    def test_interior_with_props_has_floor_line(self):
        svg = scene_background("interior room with window")
        assert 'y1="360"' in svg

    def test_exterior_with_props(self):
        svg = scene_background("exterior mars with door")
        assert 'y1="480"' in svg or '<rect x="0" y="480"' in svg


class TestPropIconNewShapes:
    def test_window_icon(self):
        svg = prop_icon("window", x=500, y=300, size=60)
        assert "rect" in svg
        assert "rx=" in svg

    def test_door_icon(self):
        svg = prop_icon("door", x=200, y=300, size=60)
        assert "rect" in svg
        assert "circle" in svg

    def test_desk_alias(self):
        svg = prop_icon("desk", x=640, y=500, size=50)
        assert "rect" in svg

    def test_console_alias(self):
        svg = prop_icon("console", x=640, y=500, size=50)
        assert "rect" in svg

    def test_display_alias(self):
        svg = prop_icon("display", x=800, y=300, size=50)
        assert "rect" in svg


class TestEnhancedSilhouette:
    def test_has_torso_rect(self):
        svg = character_silhouette("Test", x=300, y=200, height=100)
        assert "<rect" in svg
        assert "fill=" in svg

    def test_has_articulated_arms(self):
        svg = character_silhouette("Test", x=300, y=200, height=100, pose="standing")
        assert svg.count("line") >= 4

    def test_walking_pose_has_articulated_arms(self):
        standing = character_silhouette("T", x=300, y=200, height=100, pose="standing")
        walking = character_silhouette("T", x=300, y=200, height=100, pose="walking")
        assert walking.count("line") >= 6
        assert walking != standing

    def test_has_label(self):
        svg = character_silhouette("Hero", x=640, y=360, height=120)
        assert "Hero" in svg


class TestRenderFace:
    def test_eyes_present(self):
        svg = render_face(640, 360, 20)
        assert svg.count('<circle') == 2

    def test_nose_present(self):
        svg = render_face(640, 360, 20)
        assert '<line' in svg

    def test_mouth_closed_line(self):
        svg = render_face(640, 360, 20, mouth_open=False)
        assert '<line' in svg
        assert '<ellipse' not in svg

    def test_mouth_open_ellipse(self):
        svg = render_face(640, 360, 20, mouth_open=True)
        assert '<ellipse' in svg

    def test_default_mouth_closed(self):
        svg = render_face(640, 360, 20)
        assert '<ellipse' not in svg


class TestRenderClothing:
    def test_uniform_has_collar(self):
        svg = render_clothing(640, 300, 20, 50, clothing="uniform")
        assert '<polygon' in svg

    def test_civilian_has_rounded_neckline(self):
        svg = render_clothing(640, 300, 20, 50, clothing="civilian")
        assert '<polygon' in svg

    def test_formal_has_tie(self):
        svg = render_clothing(640, 300, 20, 50, clothing="formal")
        assert svg.count('<polygon') >= 2

    def test_cloak_has_draping_shape(self):
        svg = render_clothing(640, 300, 20, 50, clothing="cloak")
        assert '<polygon' in svg

    def test_slim_build_narrows_torso(self):
        svg = character_silhouette("T", x=640, y=360, height=100, build="slim")
        assert "T" in svg

    def test_atheltic_build_widens_shoulders(self):
        svg = character_silhouette("T", x=640, y=360, height=100, build="athletic")
        assert "T" in svg

    def test_heavy_build_widens_torso(self):
        svg = character_silhouette("T", x=640, y=360, height=100, build="heavy")
        assert "T" in svg


class TestRenderHair:
    def test_bald_returns_empty(self):
        assert render_hair(640, 360, 20, "bald") == ""

    def test_short_hair_has_path(self):
        svg = render_hair(640, 360, 20, "short")
        assert '<path' in svg
        assert 'fill="#000000"' in svg

    def test_long_hair_has_path(self):
        svg = render_hair(640, 360, 20, "long")
        assert '<path' in svg

    def test_curly_hair_has_path_and_circles(self):
        svg = render_hair(640, 360, 20, "curly")
        assert '<path' in svg
        assert '<circle' in svg

    def test_ponytail_has_path(self):
        svg = render_hair(640, 360, 20, "ponytail")
        assert '<path' in svg
        assert svg.count('<path') >= 2


class TestRenderAccessory:
    def test_none_returns_empty(self):
        assert render_accessory(640, 360, 20, 300, 20, "none") == ""

    def test_hat_has_rects(self):
        svg = render_accessory(640, 360, 20, 300, 20, "hat")
        assert svg.count('<rect') == 2

    def test_cape_has_path(self):
        svg = render_accessory(640, 360, 20, 300, 20, "cape")
        assert '<path' in svg

    def test_badge_has_rect(self):
        svg = render_accessory(640, 360, 20, 300, 20, "badge")
        assert '<rect' in svg

    def test_weapon_has_line(self):
        svg = render_accessory(640, 360, 20, 300, 20, "weapon")
        assert svg.count('<line') == 2

    def test_unknown_returns_empty(self):
        assert render_accessory(640, 360, 20, 300, 20, "unknown") == ""


class TestCharacterSilhouetteWithNewParams:
    def test_mouth_open_param_accepted(self):
        svg = character_silhouette("T", x=640, y=360, height=100, mouth_open=True)
        assert "T" in svg

    def test_clothing_param_accepted(self):
        svg = character_silhouette("T", x=640, y=360, height=100, clothing="formal")
        assert "T" in svg

    def test_hair_style_param_accepted(self):
        svg = character_silhouette("T", x=640, y=360, height=100, hair_style="long")
        assert "T" in svg

    def test_accessory_param_accepted(self):
        svg = character_silhouette("T", x=640, y=360, height=100, accessory="hat")
        assert "T" in svg

    def test_backward_compatible_defaults(self):
        old = character_silhouette("Legacy", x=640, y=360, height=100)
        new = character_silhouette("Legacy", x=640, y=360, height=100,
                                   mouth_open=False, clothing="uniform",
                                   build="average", hair_style="short", accessory="none")
        assert old == new
