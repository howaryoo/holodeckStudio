from __future__ import annotations

from holodeck.agents.video.ffmpeg_utils import (
    DEFAULT_PITCH_MAP,
    _semitone_factor,
    build_audio_mix_cmd,
    build_frame_concat_cmd,
    build_pitch_shift_cmd,
)


class TestBuildFrameConcatCmd:
    def test_concat_cmd_has_expected_flags(self):
        args, stdin = build_frame_concat_cmd(
            ["/tmp/frame_0000.png", "/tmp/frame_0001.png"],
            "/out/video.mp4",
        )
        assert args[0] == "ffmpeg"
        assert "-y" in args
        assert "-f" in args
        assert "concat" in args[args.index("-f") + 1 : args.index("-f") + 2][0]
        assert "-safe" in args

    def test_concat_stdin_content(self):
        _, stdin = build_frame_concat_cmd(
            ["frame_0.png", "frame_1.png", "frame_2.png"],
            "out.mp4",
        )
        lines = stdin.decode().strip().split("\n")
        assert len(lines) == 3
        assert all(l.startswith("file ") for l in lines)
        assert "frame_0.png" in lines[0]

    def test_bw_filter_included_by_default(self):
        args, _ = build_frame_concat_cmd(
            ["f.png"], "out.mp4", fps=24, bw=True
        )
        vf_idx = args.index("-vf")
        filter_str = args[vf_idx + 1]
        assert "colorchannelmixer" in filter_str
        assert ".3:" in filter_str

    def test_bw_filter_omitted_when_bw_false(self):
        args, _ = build_frame_concat_cmd(
            ["f.png"], "out.mp4", fps=24, bw=False
        )
        vf_idx = args.index("-vf")
        filter_str = args[vf_idx + 1]
        assert "colorchannelmixer" not in filter_str

    def test_fps_setting(self):
        args, _ = build_frame_concat_cmd(
            ["f.png"], "out.mp4", fps=12, bw=False
        )
        vf_idx = args.index("-vf")
        filter_str = args[vf_idx + 1]
        assert "fps=12" in filter_str

    def test_concat_output_path(self):
        args, _ = build_frame_concat_cmd(
            ["f.png"], "/final/video.mp4"
        )
        assert args[-1] == "/final/video.mp4"

    def test_concat_uses_libx264(self):
        args, _ = build_frame_concat_cmd(["f.png"], "out.mp4")
        assert "-c:v" in args
        assert "libx264" in args[args.index("-c:v") + 1]


class TestBuildAudioMixCmd:
    def test_no_audio_copy_mode(self):
        cmd = build_audio_mix_cmd("video.mp4", [], "out.mp4")
        assert cmd[0] == "ffmpeg"
        assert "-c" in cmd
        assert "copy" in cmd[cmd.index("-c") + 1]

    def test_single_audio_concat(self):
        cmd = build_audio_mix_cmd(
            "video.mp4", ["audio.mp3"], "out.mp4"
        )
        assert "-filter_complex" in cmd
        mix_idx = cmd.index("-filter_complex") + 1
        assert "concat=n=1:v=0:a=1" in cmd[mix_idx]

    def test_multiple_audio_concat(self):
        cmd = build_audio_mix_cmd(
            "video.mp4", ["a1.mp3", "a2.mp3", "a3.mp3"], "out.mp4"
        )
        mix_idx = cmd.index("-filter_complex") + 1
        assert "concat=n=3:v=0:a=1" in cmd[mix_idx]

    def test_audio_inputs_present(self):
        cmd = build_audio_mix_cmd("vid.mp4", ["a.mp3", "b.mp3"], "mix.mp4")
        video_input = cmd.index("-i")
        assert cmd[video_input + 1] == "vid.mp4"
        audio_inputs = [i for i, x in enumerate(cmd) if x == "-i"]
        assert len(audio_inputs) == 3

    def test_map_flags_present(self):
        cmd = build_audio_mix_cmd("v.mp4", ["a.mp3"], "o.mp4")
        assert "-map" in cmd
        assert "[aout]" in cmd

    def test_concat_filter_format(self):
        cmd = build_audio_mix_cmd("v.mp4", ["a.mp3", "b.mp3"], "o.mp4")
        mix_idx = cmd.index("-filter_complex") + 1
        expected = "[1:a][2:a]concat=n=2:v=0:a=1[aout]"
        assert cmd[mix_idx] == expected

    def test_aac_codec_used(self):
        cmd = build_audio_mix_cmd("v.mp4", ["a.mp3"], "o.mp4")
        assert "-c:a" in cmd
        assert "aac" in cmd[cmd.index("-c:a") + 1]

    def test_video_codec_copy(self):
        cmd = build_audio_mix_cmd("v.mp4", ["a.mp3"], "o.mp4")
        assert "-c:v" in cmd
        assert "copy" in cmd[cmd.index("-c:v") + 1]

    def test_shortest_flag(self):
        cmd = build_audio_mix_cmd("v.mp4", ["a.mp3"], "o.mp4")
        assert "-shortest" in cmd

    def test_output_path_correct(self):
        cmd = build_audio_mix_cmd("v.mp4", ["a.mp3"], "/output/final.mp4")
        assert cmd[-1] == "/output/final.mp4"


class TestBuildPitchShiftCmd:
    def test_returns_ffmpeg_cmd(self):
        cmd = build_pitch_shift_cmd("in.mp3", -2.0, "out.mp3")
        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd

    def test_audio_filter_asetrate_aresample(self):
        cmd = build_pitch_shift_cmd("voice.mp3", 3.0, "pitched.mp3")
        af_idx = cmd.index("-af") + 1
        assert "asetrate=44100*" in cmd[af_idx]
        assert "aresample=44100" in cmd[af_idx]

    def test_semitone_factor_zero(self):
        assert _semitone_factor(0.0) == 1.0

    def test_semitone_factor_negative(self):
        assert _semitone_factor(-2.0) < 1.0
        assert _semitone_factor(-12.0) == 0.5

    def test_semitone_factor_positive(self):
        assert _semitone_factor(3.0) > 1.0
        assert _semitone_factor(12.0) == 2.0

    def test_default_pitch_map_keys(self):
        assert "male" in DEFAULT_PITCH_MAP
        assert "female" in DEFAULT_PITCH_MAP
        assert "neutral" in DEFAULT_PITCH_MAP

    def test_default_pitch_map_values(self):
        assert DEFAULT_PITCH_MAP["male"] == -2.0
        assert DEFAULT_PITCH_MAP["female"] == 3.0
        assert DEFAULT_PITCH_MAP["neutral"] == 0.0

    def test_male_pitch_factor(self):
        factor = _semitone_factor(DEFAULT_PITCH_MAP["male"])
        assert round(factor, 4) == 0.8909

    def test_female_pitch_factor(self):
        factor = _semitone_factor(DEFAULT_PITCH_MAP["female"])
        assert round(factor, 4) == 1.1892
