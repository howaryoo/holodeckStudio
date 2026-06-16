from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model

_PIPER_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "piper_models"

_DEFAULT_PIPER_MODELS: dict[str, str] = {
    "female": "en_US-lessac-medium",
    "male": "en_US-libritts_r-medium",
}


def _has_gtts() -> bool:
    import importlib.util
    return importlib.util.find_spec("gtts") is not None


def _has_piper() -> bool:
    import importlib.util
    if importlib.util.find_spec("piper") is None:
        return False
    for key in ("female", "male"):
        model_path = _PIPER_MODELS_DIR / f"{_DEFAULT_PIPER_MODELS[key]}.onnx"
        if not model_path.exists():
            return False
    return True


def _get_piper_model_path(gender: str) -> str:
    name = _DEFAULT_PIPER_MODELS.get(gender, _DEFAULT_PIPER_MODELS["female"])
    return str(_PIPER_MODELS_DIR / f"{name}.onnx")


def _get_voice_model(char_name: str, character_visuals: dict) -> str:
    cv = character_visuals.get(char_name, {})
    return cv.get("voice_model", "")


def _wav_to_mp3(wav_path: str, mp3_path: str) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path],
            capture_output=True, text=True, check=True,
        )
        return True
    except Exception:
        return False


def _synthesize_with_piper(
    text: str, model_path: str, wav_path: str, speaker: int | None = None
) -> bool:
    try:
        from piper import PiperVoice

        voice = PiperVoice.load(model_path)
        import wave

        with wave.open(wav_path, "wb") as wf:
            voice.synthesize_wav(text, wf, speaker_id=speaker)
        return True
    except Exception:
        return False


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = re.sub(r"^>\s*", "", text)
    text = re.sub(r"^[•\-]\s*", "", text)
    text = text.strip()
    return text


def _find_center_characters(script: str) -> set[str]:
    chars: set[str] = set()
    for m in re.finditer(r"<center>([^<]+)</center>", script):
        c = _clean_text(m.group(1))
        if c:
            chars.add(c.upper())
    return chars


def _find_colon_characters(script: str, min_dialogue: int = 5) -> set[str]:
    chars: set[str] = set()
    for m in re.finditer(r"^[>\s]*\*{0,2}([A-Z][A-Za-z\s]+?)\*{0,2}\s*:\s*(.{" + str(min_dialogue) + r",})$", script, re.MULTILINE):
        c = _clean_text(m.group(1))
        if c and len(c) >= 2:
            chars.add(c.upper())
    return chars


def _parse_dialogue_lines(script: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    center_chars = _find_center_characters(script)

    center_pattern = re.compile(r"<center>([^<]+)</center>\s*\n\s*[>]?\s*(.+)", re.MULTILINE)
    for m in center_pattern.finditer(script):
        char = _clean_text(m.group(1))
        dialogue = _clean_text(m.group(2))
        if char and dialogue and len(dialogue) > 5:
            lines.append((char, dialogue))

    if center_chars:
        valid_chars = center_chars
    else:
        valid_chars = _find_colon_characters(script, 5)

    colon_pattern = re.compile(r"^[>\s]*\*{0,2}([A-Z][A-Za-z\s]+?)\*{0,2}\s*:\s*(.+)$", re.MULTILINE)
    for m in colon_pattern.finditer(script):
        char = _clean_text(m.group(1))
        dialogue = _clean_text(m.group(2))
        if char and dialogue and len(dialogue) > 5:
            if valid_chars:
                if char.upper() not in valid_chars:
                    continue
            if not any(c == char and d == dialogue for c, d in lines):
                lines.append((char, dialogue))

    if not lines:
        for line in script.split("\n"):
            cleaned = _clean_text(line)
            if cleaned and len(cleaned) > 15 and not line.startswith("**") and not line.startswith("INT.") and not line.startswith("EXT.") and not line.startswith("<"):
                lines.append(("Narrator", cleaned))

    return lines


class VoiceSynthesisAgent:
    stage = StageType.AUDIO
    _agent: Agent | None = None

    def __init__(self, model: Model | None = None) -> None:
        self._model = model

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Voice Synthesizer",
                role=(
                    "Synthesize dialogue audio using piper-tts (neural) or gTTS (fallback). "
                    "Parse character lines and generate per-line .mp3 with multi-voice support."
                ),
                instructions=[
                    "Parse the script for character dialogue lines.",
                    "Generate .mp3 per line via piper-tts (preferred) or gTTS (fallback).",
                    "Use per-character voice models from character_visuals when available.",
                    "Return file paths to generated audio.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("script"):
            return ValidationResult(valid=False, errors=["Script required for voice synthesis"])
        return ValidationResult(valid=True)

    @observe(name="voice_synthesis.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        script = context.get("script", "")
        lines = _parse_dialogue_lines(script)
        character_visuals: dict = context.get("character_visuals", {})

        import os

        media_dir = os.path.join(
            context.get("output_dir", "./output"),
            "media",
            str(context.get("production_id", "unknown")),
        )
        os.makedirs(media_dir, exist_ok=True)

        use_piper = _has_piper()
        audio_urls = []
        tts_engine = "none"

        if use_piper:
            tts_engine = "piper"
            for i, (char, text) in enumerate(lines[:50]):
                fname = f"dialogue_{i:04d}_{char[:10].replace(' ', '_')}"
                wav_path = os.path.join(media_dir, f"{fname}.wav")
                mp3_path = os.path.join(media_dir, f"{fname}.mp3")
                voice_model = _get_voice_model(char, character_visuals)
                gender = "female" if voice_model.lower() in ("female", "f") else "male"
                model_path = _get_piper_model_path(gender)
                try:
                    if _synthesize_with_piper(text, model_path, wav_path):
                        if _wav_to_mp3(wav_path, mp3_path):
                            audio_urls.append(str(mp3_path))
                            os.remove(wav_path)
                        else:
                            audio_urls.append(str(wav_path))
                except Exception:
                    continue

        if not audio_urls and _has_gtts():
            tts_engine = "gtts"
            from gtts import gTTS

            for i, (char, text) in enumerate(lines[:50]):
                try:
                    tts = gTTS(text=text, lang="en", tld="com", slow=False)
                    fname = f"dialogue_{i:04d}_{char[:10].replace(' ', '_')}.mp3"
                    fpath = os.path.join(media_dir, fname)
                    tts.save(fpath)
                    audio_urls.append(str(fpath))
                except Exception:
                    continue

        context["dialogue_audio_urls"] = audio_urls
        return AgentOutput(
            content=f"Generated {len(audio_urls)} dialogue audio files using {tts_engine}.",
            metadata={
                "stage": "audio",
                "agent": "voice_synthesis",
                "audio_urls": audio_urls,
                "tts_engine": tts_engine,
            },
        )

    @observe(name="voice_synthesis.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        urls = []
        if output.metadata:
            urls = output.metadata.get("audio_urls", [])
        if not urls:
            return ReviewResult(approved=False, score=0, feedback="No audio generated.")
        engine = output.metadata.get("tts_engine", "unknown")
        return ReviewResult(
            approved=True, score=85,
            feedback=f"{len(urls)} audio files generated using {engine}.",
        )
