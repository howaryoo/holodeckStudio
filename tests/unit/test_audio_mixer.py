from __future__ import annotations

import os
import tempfile

from holodeck.agents.audio.audio_mixer import AudioMixer


def _make_silent_mp3(path: str, duration_sec: float = 1.0) -> str:
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
         "-t", str(duration_sec), "-c:a", "libmp3lame", "-b:a", "128k", path],
        capture_output=True,
    )
    return path


def test_mix_scene_dialogue_only():
    with tempfile.TemporaryDirectory() as td:
        dia = _make_silent_mp3(os.path.join(td, "dialogue.mp3"))
        out = os.path.join(td, "output.mp3")
        mixer = AudioMixer()
        result = mixer.mix_scene(dialogue_path=dia, output_path=out, scene_duration=1.0)
        assert result == out
        assert os.path.exists(out)


def test_mix_scene_with_ambience():
    with tempfile.TemporaryDirectory() as td:
        dia = _make_silent_mp3(os.path.join(td, "dialogue.mp3"))
        amb = _make_silent_mp3(os.path.join(td, "ambience.mp3"), duration_sec=5.0)
        out = os.path.join(td, "output.mp3")
        mixer = AudioMixer()
        result = mixer.mix_scene(
            dialogue_path=dia, ambience_path=amb,
            output_path=out, scene_duration=2.0,
        )
        assert result == out
        assert os.path.exists(out)


def test_mix_scene_with_sfx():
    with tempfile.TemporaryDirectory() as td:
        dia = _make_silent_mp3(os.path.join(td, "dialogue.mp3"))
        sfx1 = _make_silent_mp3(os.path.join(td, "sfx1.mp3"))
        sfx2 = _make_silent_mp3(os.path.join(td, "sfx2.mp3"))
        out = os.path.join(td, "output.mp3")
        mixer = AudioMixer()
        result = mixer.mix_scene(
            dialogue_path=dia, sfx_paths=[sfx1, sfx2],
            output_path=out, scene_duration=2.0,
        )
        assert result == out
        assert os.path.exists(out)


def test_concat_scenes():
    with tempfile.TemporaryDirectory() as td:
        s1 = _make_silent_mp3(os.path.join(td, "s1.mp3"), 1.0)
        s2 = _make_silent_mp3(os.path.join(td, "s2.mp3"), 1.0)
        out = os.path.join(td, "concat.mp3")
        mixer = AudioMixer()
        result = mixer.concat_scenes([s1, s2], out)
        assert result == out
        assert os.path.exists(out)


def test_concat_single_scene():
    with tempfile.TemporaryDirectory() as td:
        s1 = _make_silent_mp3(os.path.join(td, "s1.mp3"), 1.0)
        out = os.path.join(td, "out.mp3")
        mixer = AudioMixer()
        result = mixer.concat_scenes([s1], out)
        assert result == out
        assert os.path.exists(out)


def test_concat_empty_list():
    mixer = AudioMixer()
    assert mixer.concat_scenes([], "out.mp3") is None


def test_get_duration():
    with tempfile.TemporaryDirectory() as td:
        path = _make_silent_mp3(os.path.join(td, "test.mp3"), 2.5)
        mixer = AudioMixer()
        dur = mixer.get_duration(path)
        assert 2.0 <= dur <= 3.0
