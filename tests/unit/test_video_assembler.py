from __future__ import annotations

from holodeck.agents.video.video_assembler import (
    _build_camera_move_filter,
    _build_xfade_filtergraph,
    _COLOR_PRESETS,
    _escape_drawtext,
    _group_by_scene,
    _interpolate_zoom,
    _resolve_color_filter,
    build_drawtext_filters,
)


class TestEscapeDrawtext:
    def test_plain_text_unchanged(self):
        assert _escape_drawtext("Hello world") == "Hello world"

    def test_colon_escaped(self):
        assert _escape_drawtext("Time: 2pm") == "Time\\: 2pm"

    def test_backslash_escaped(self):
        assert _escape_drawtext("path\\to") == "path\\\\to"

    def test_percent_escaped(self):
        assert _escape_drawtext("100% done") == "100\\% done"

    def test_single_quote_escaped(self):
        result = _escape_drawtext("it's fine")
        assert "\\'" in result or "'\\''" in result

    def test_all_special_chars(self):
        text = "It's 100% done: path\\test"
        result = _escape_drawtext(text)
        assert "\\%" in result
        assert "\\:" in result
        assert "\\\\" in result


class TestBuildDrawtextFilters:
    def test_empty_data_returns_empty(self):
        assert build_drawtext_filters([], 4.0) == ""

    def test_single_line(self):
        data = [{"frame_index": 0, "dialogue_text": "Hello"}]
        result = build_drawtext_filters(data, 5.0)
        assert "drawtext=" in result
        assert "text='Hello'" in result
        assert "enable='between(t,0.0,5.0)'" in result
        assert "x=(w-text_w)/2" in result
        assert "y=h-50" in result
        assert "fontcolor=white" in result
        assert "fontsize=24" in result
        assert "box=1" in result
        assert "boxcolor=black@0.5" in result
        assert "boxborderw=5" in result

    def test_multiple_lines(self):
        data = [
            {"frame_index": 0, "dialogue_text": "First"},
            {"frame_index": 1, "dialogue_text": "Second"},
        ]
        result = build_drawtext_filters(data, 3.0)
        assert result.count("drawtext=") == 2
        assert "text='First'" in result
        assert "text='Second'" in result
        assert "between(t,0.0,3.0)" in result
        assert "between(t,3.0,6.0)" in result

    def test_timing_from_frame_index(self):
        data = [{"frame_index": 2, "dialogue_text": "Late"}]
        result = build_drawtext_filters(data, 4.5)
        assert "between(t,9.0,13.5)" in result

    def test_text_escaped_in_filter(self):
        data = [{"frame_index": 0, "dialogue_text": "It's 100%: yes"}]
        result = build_drawtext_filters(data, 2.0)
        assert "\\%" in result
        assert "\\:" in result

    def test_character_key_optional(self):
        data = [{"frame_index": 0, "dialogue_text": "Hi"}]
        result = build_drawtext_filters(data, 1.0)
        assert "text='Hi'" in result

    def test_frame_count_spans_multiple_sub_frames(self):
        data = [{"frame_index": 0, "frame_count": 3, "dialogue_text": "Hello"}]
        result = build_drawtext_filters(data, 2.0)
        assert "between(t,0.0,6.0)" in result


class TestGroupByScene:
    def test_single_scene(self):
        sd = [{"frame_index": i, "scene": "1"} for i in range(3)]
        png = [f"f{i}.png" for i in range(3)]
        groups = _group_by_scene(sd, png)
        assert len(groups) == 1
        assert groups[0][0] == "1"
        assert len(groups[0][1]) == 3

    def test_multiple_scenes(self):
        sd = [
            {"frame_index": 0, "scene": "1"},
            {"frame_index": 1, "scene": "1"},
            {"frame_index": 2, "scene": "2"},
        ]
        png = ["f0.png", "f1.png", "f2.png"]
        groups = _group_by_scene(sd, png)
        assert len(groups) == 2
        assert groups[0][0] == "1"
        assert groups[1][0] == "2"
        assert len(groups[0][1]) == 2
        assert len(groups[1][1]) == 1

    def test_scene_order_by_appearance(self):
        sd = [
            {"frame_index": 2, "scene": "2"},
            {"frame_index": 0, "scene": "1"},
            {"frame_index": 1, "scene": "1"},
        ]
        png = ["f0.png", "f1.png", "f2.png"]
        groups = _group_by_scene(sd, png)
        assert groups[0][0] == "1"
        assert groups[1][0] == "2"

    def test_default_scene_when_missing(self):
        sd = [{"frame_index": 0}, {"frame_index": 1}]
        png = ["f0.png", "f1.png"]
        groups = _group_by_scene(sd, png)
        assert len(groups) == 1
        assert groups[0][0] == "1"

    def test_png_files_match_subtitle_data(self):
        sd = [{"frame_index": 0, "scene": "1"}]
        png = ["path/frame_0000.png"]
        groups = _group_by_scene(sd, png)
        assert groups[0][1][0] == "path/frame_0000.png"

    def test_sub_frames_mapped_by_frame_index(self):
        sd = [{"frame_index": 0, "frame_count": 3, "scene": "1"}]
        png = ["f0.png", "f1.png", "f2.png"]
        groups = _group_by_scene(sd, png)
        assert len(groups[0][1]) == 3

    def test_subtitle_data_returned_per_scene(self):
        sd = [{"frame_index": 0, "frame_count": 2, "scene": "1"}]
        png = ["f0.png", "f1.png"]
        groups = _group_by_scene(sd, png)
        assert len(groups[0][2]) == 1  # 1 subtitle entry


class TestBuildXfadeFiltergraph:
    def test_single_scene_no_xfade(self):
        fg, label = _build_xfade_filtergraph([5.0])
        assert fg == ""
        assert label == "[0:v]"

    def test_two_scenes(self):
        fg, label = _build_xfade_filtergraph([5.0, 3.0])
        assert "xfade=" in fg
        assert "offset=4.0" in fg or "offset=4" in fg
        assert "duration=1" in fg
        assert "transition=fadeblack" in fg
        assert "format=yuv420p" in fg
        assert label == "v0"

    def test_three_scenes_cascaded(self):
        fg, label = _build_xfade_filtergraph([5.0, 3.0, 4.0])
        assert fg.count("xfade=") == 2
        assert ";[" in fg  # cascaded
        assert label == "v1"

    def test_offset_calculation(self):
        fg, _ = _build_xfade_filtergraph([10.0, 5.0, 3.0], "fadeblack", 1.0)
        assert "offset=9.0" in fg  # first: 10 - 1
        assert "offset=13.0" in fg or "offset=14.0" in fg  # second: 10+5-2=13

    def test_custom_transition(self):
        fg, _ = _build_xfade_filtergraph([4.0, 4.0], "fadewhite", 0.5)
        assert "transition=fadewhite" in fg
        assert "duration=0.5" in fg


_NOIR_FILTER = "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0"

class TestResolveColorFilter:
    def test_no_moods_defaults_noir(self):
        assert _resolve_color_filter(None, "1") == _NOIR_FILTER

    def test_empty_dict_defaults_noir(self):
        assert _resolve_color_filter({}, "1") == _NOIR_FILTER

    def test_warm_mood(self):
        result = _resolve_color_filter({"1": "warm"}, "1")
        assert "colorbalance=" in result
        assert "rs=.15" in result
        assert "gs=.05" in result
        assert "bs=-.1" in result

    def test_cool_mood(self):
        result = _resolve_color_filter({"1": "cool"}, "1")
        assert "colorbalance=" in result
        assert "rs=-.1" in result
        assert "bs=.2" in result

    def test_sepia_mood(self):
        result = _resolve_color_filter({"scene_A": "sepia"}, "scene_A")
        assert "colorchannelmixer=.393:.769:.189" in result

    def test_vivid_mood(self):
        result = _resolve_color_filter({"1": "vivid"}, "1")
        assert "eq=saturation=1.5" in result

    def test_neutral_mood_returns_none(self):
        assert _resolve_color_filter({"1": "neutral"}, "1") is None

    def test_unknown_mood_falls_back_to_noir(self):
        result = _resolve_color_filter({"1": "rainbow"}, "1")
        assert ".3:.4:.3" in result

    def test_missing_scene_id_falls_back_to_noir(self):
        result = _resolve_color_filter({"other": "warm"}, "1")
        assert ".3:.4:.3" in result

    def test_color_presets_all_keys_have_valid_format(self):
        for name, val in _COLOR_PRESETS.items():
            if val is None:
                continue
            assert "=" in val, f"Preset '{name}' missing '=' in filter string"


class TestInterpolateZoom:
    def test_zoom_from_1_to_2(self):
        expr = _interpolate_zoom(1.0, 2.0, 100)
        assert "1.03+1.0*on/100" in expr

    def test_zoom_from_1_to_3(self):
        expr = _interpolate_zoom(1.03, 3.16, 200)
        assert "1.03+2.13*on/200" in expr

    def test_zoom_no_change(self):
        expr = _interpolate_zoom(1.0, 1.0, 50)
        assert "1.03+0.0*on/50" in expr

    def test_total_frames_in_denominator(self):
        expr = _interpolate_zoom(1.0, 2.0, 75)
        assert "on/75" in expr


class TestBuildCameraMoveFilter:
    def test_no_camera_moves_returns_none(self):
        assert _build_camera_move_filter(None, "1", 100) is None

    def test_empty_list_returns_none(self):
        assert _build_camera_move_filter([], "1", 100) is None

    def test_no_matching_scene_returns_none(self):
        moves = [{"scene": "2", "start_zoom": 1.0, "end_zoom": 2.0}]
        assert _build_camera_move_filter(moves, "1", 100) is None

    def test_zoom_only_move(self):
        moves = [{"scene": "1", "start_zoom": 1.0, "end_zoom": 2.0,
                   "pan_x_start": 0, "pan_x_end": 0,
                   "pan_y_start": 0, "pan_y_end": 0,
                   "duration_frames": 100}]
        result = _build_camera_move_filter(moves, "1", 100)
        assert result is not None
        assert "crop=" in result
        assert "scale=1280:720" in result
        assert "1.0+(2.0-1.0)*on/100" in result

    def test_pan_and_zoom(self):
        moves = [{"scene": "scene_1", "start_zoom": 1.5, "end_zoom": 3.0,
                   "pan_x_start": 0, "pan_x_end": 100,
                   "pan_y_start": 50, "pan_y_end": 0,
                   "duration_frames": 200}]
        result = _build_camera_move_filter(moves, "scene_1", 200)
        assert "crop=" in result
        assert "1.5+(3.0-1.5)*on/200" in result
        assert "0+(100-0)*on/200" in result
        assert "50+(0-50)*on/200" in result

    def test_default_duration_fallback(self):
        moves = [{"scene": "1", "start_zoom": 1.0, "end_zoom": 2.0,
                   "pan_x_start": 0, "pan_x_end": 0,
                   "pan_y_start": 0, "pan_y_end": 0}]
        result = _build_camera_move_filter(moves, "1", 50)
        assert "on/50" in result
