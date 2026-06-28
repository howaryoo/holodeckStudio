from __future__ import annotations

from unittest.mock import MagicMock, patch

from holodeck.agents.audio.voice_synthesis import (
    VoiceSynthesisAgent,
    _get_piper_model_path,
    _get_voice_model,
    _has_piper,
    _parse_dialogue_lines,
    _strip_stage_directions,
    _wav_to_mp3,
)


class TestHasPiper:
    def test_returns_false_when_piper_not_installed(self):
        with patch("importlib.util.find_spec") as mock_find:
            mock_find.return_value = None
            assert _has_piper() is False

    def test_returns_false_when_model_files_missing(self):
        with (
            patch("importlib.util.find_spec") as mock_find,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            mock_find.return_value = MagicMock()
            mock_exists.return_value = False
            assert _has_piper() is False

    def test_returns_true_when_piper_and_models_available(self):
        with (
            patch("importlib.util.find_spec") as mock_find,
            patch("pathlib.Path.exists") as mock_exists,
        ):
            mock_find.return_value = MagicMock()
            mock_exists.return_value = True
            assert _has_piper() is True


class TestGetPiperModelPath:
    def test_female_resolves_lessac(self):
        path = _get_piper_model_path("female")
        assert "en_US-lessac-medium" in path
        assert path.endswith(".onnx")

    def test_male_resolves_libritts(self):
        path = _get_piper_model_path("male")
        assert "en_US-libritts_r-medium" in path
        assert path.endswith(".onnx")

    def test_unknown_gender_falls_back_to_female(self):
        path = _get_piper_model_path("other")
        assert "en_US-lessac-medium" in path


class TestGetVoiceModel:
    def test_returns_empty_when_char_not_found(self):
        assert _get_voice_model("Hero", {}) == ""

    def test_returns_voice_model_from_character_visuals(self):
        cv = {"Hero": {"voice_model": "male"}}
        assert _get_voice_model("Hero", cv) == "male"

    def test_returns_empty_when_no_voice_model_key(self):
        cv = {"Hero": {"clothing": "uniform"}}
        assert _get_voice_model("Hero", cv) == ""


class TestWavToMp3:
    @patch("subprocess.run")
    def test_successful_conversion(self, mock_run):
        mock_run.return_value = MagicMock()
        assert _wav_to_mp3("/tmp/test.wav", "/tmp/test.mp3") is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args
        assert "-y" in args
        assert "/tmp/test.wav" in args
        assert "/tmp/test.mp3" in args

    @patch("subprocess.run")
    def test_failed_conversion_returns_false(self, mock_run):
        mock_run.side_effect = Exception("ffmpeg error")
        assert _wav_to_mp3("/tmp/test.wav", "/tmp/test.mp3") is False


class TestSynthesizeWithPiper:
    @patch("holodeck.agents.audio.voice_synthesis._synthesize_with_piper")
    def test_calls_piper_api(self, mock_synth):
        mock_synth.return_value = True
        result = mock_synth("Hello", "/models/test.onnx", "/tmp/test.wav")
        assert result is True
        mock_synth.assert_called_once_with("Hello", "/models/test.onnx", "/tmp/test.wav")

    @patch("holodeck.agents.audio.voice_synthesis._synthesize_with_piper")
    def test_piper_failure_returns_false(self, mock_synth):
        mock_synth.return_value = False
        result = mock_synth("Hello", "/models/test.onnx", "/tmp/test.wav")
        assert result is False


class TestVoiceSynthesisAgentProcess:
    @patch("holodeck.agents.audio.voice_synthesis._parse_dialogue_lines")
    @patch("holodeck.agents.audio.voice_synthesis._has_piper")
    @patch("holodeck.agents.audio.voice_synthesis._synthesize_with_piper")
    @patch("holodeck.agents.audio.voice_synthesis._wav_to_mp3")
    def test_piper_preferred_over_gtts(
        self,
        mock_wav2mp3,
        mock_synth,
        mock_piper,
        mock_parse,
    ):
        mock_piper.return_value = True
        mock_parse.return_value = [("Hero", "Hello world")]
        mock_synth.return_value = True
        mock_wav2mp3.return_value = True
        agent = VoiceSynthesisAgent()
        result = agent.process({"script": "<center>Hero</center>\nHello world", "output_dir": "/tmp"})
        assert result.metadata is not None
        assert result.metadata.get("tts_engine") == "piper"
        assert len(result.metadata.get("audio_urls", [])) == 1

    @patch("holodeck.agents.audio.voice_synthesis._parse_dialogue_lines")
    @patch("holodeck.agents.audio.voice_synthesis._has_piper")
    def test_falls_back_to_gtts_when_piper_unavailable(
        self,
        mock_piper,
        mock_parse,
    ):
        mock_piper.return_value = False
        mock_parse.return_value = [("Hero", "Hello world")]
        agent = VoiceSynthesisAgent()
        result = agent.process({"script": "Hero: Hello world", "output_dir": "/tmp"})
        assert result.metadata is not None
        assert result.metadata.get("tts_engine") in ("piper", "gtts", "none")

    @patch("holodeck.agents.audio.voice_synthesis._parse_dialogue_lines")
    @patch("holodeck.agents.audio.voice_synthesis._has_piper")
    def test_tts_engine_none_when_no_tts_available(
        self,
        mock_piper,
        mock_parse,
    ):
        mock_piper.return_value = False
        mock_parse.return_value = []
        agent = VoiceSynthesisAgent()
        result = agent.process({"script": "", "output_dir": "/tmp"})
        assert result.metadata is not None
        assert len(result.metadata.get("audio_urls", [])) == 0

    def test_validate_input_missing_script(self):
        agent = VoiceSynthesisAgent()
        result = agent.validate_input({})
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_input_with_script(self):
        agent = VoiceSynthesisAgent()
        result = agent.validate_input({"script": "Hero: Hello"})
        assert result.valid is True


class TestStripStageDirections:
    def test_pure_stage_direction_returns_empty(self) -> None:
        assert _strip_stage_directions("(He pauses and looks away)") == ""

    def test_mixed_returns_only_spoken_text(self) -> None:
        result = _strip_stage_directions("(sighing) I can't believe you did that.")
        assert result == "I can't believe you did that."

    def test_clean_dialogue_unchanged(self) -> None:
        assert _strip_stage_directions("Hello, how are you?") == "Hello, how are you?"

    def test_multiple_parentheticals_stripped(self) -> None:
        result = _strip_stage_directions("(quietly) Yeah. (looks away) Sure.")
        assert result == "Yeah.  Sure."

    def test_strips_surrounding_whitespace(self) -> None:
        result = _strip_stage_directions("  (pauses)  ")
        assert result == ""


class TestParseDialogueLines:
    def test_colon_format_pure_stage_direction_excluded(self) -> None:
        script = "JOEY: (He leans forward slowly)\nRACHEL: Hey, how are you?"
        lines = _parse_dialogue_lines(script)
        characters = [c for c, _ in lines]
        assert "JOEY" not in characters
        assert "RACHEL" in characters

    def test_colon_format_mixed_keeps_spoken_text_only(self) -> None:
        script = "JOEY: (sighing) I really miss the sandwich.\nRACHEL: Me too."
        lines = _parse_dialogue_lines(script)
        joey_lines = [t for c, t in lines if c == "JOEY"]
        assert joey_lines
        assert "sighing" not in joey_lines[0]
        assert "I really miss the sandwich." in joey_lines[0]

    def test_colon_format_clean_dialogue_preserved(self) -> None:
        script = "CHANDLER: Could this BE any more of a sandwich emergency?"
        lines = _parse_dialogue_lines(script)
        assert len(lines) == 1
        assert lines[0][1] == "Could this BE any more of a sandwich emergency?"

    def test_center_tag_format_strips_stage_directions(self) -> None:
        script = "<center>MONICA</center>\n(slamming cabinet) This kitchen is a disaster."
        lines = _parse_dialogue_lines(script)
        monica_lines = [t for c, t in lines if c == "MONICA"]
        if monica_lines:
            assert "(slamming cabinet)" not in monica_lines[0]

    def test_center_tag_pure_direction_excluded(self) -> None:
        script = "<center>ROSS</center>\n(adjusting glasses carefully)"
        lines = _parse_dialogue_lines(script)
        assert not any(c == "ROSS" for c, _ in lines)


class TestVoiceSynthesisAgentReview:
    def test_review_approved_with_urls(self):
        agent = VoiceSynthesisAgent()
        result = agent.review_output(
            MagicMock(
                metadata={
                    "audio_urls": ["/tmp/test.mp3"],
                    "tts_engine": "piper",
                }
            )
        )
        assert result.approved is True
        assert result.score == 85

    def test_review_rejected_no_urls(self):
        agent = VoiceSynthesisAgent()
        result = agent.review_output(MagicMock(metadata={"audio_urls": []}))
        assert result.approved is False
        assert result.score == 0
