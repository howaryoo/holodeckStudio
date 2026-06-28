from __future__ import annotations

import asyncio
import concurrent.futures
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model

    from holodeck.agents.audio.voice_provider import VoiceSynthesisProvider

_PIPER_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "piper_models"


def _run_provider_in_thread(
    provider: VoiceSynthesisProvider,
    text: str,
    char_name: str,
    output_path: str,
    context: dict,  # type: ignore[type-arg]
) -> bool:
    """Run an async provider.synthesize() in a fresh event loop on a worker thread.

    Required because VoiceSynthesisAgent.process() is sync but providers are async,
    and the pipeline may already have a running event loop on the calling thread.
    """
    loop = asyncio.new_event_loop()
    try:
        coro = provider.synthesize(text, char_name, output_path, context)
        return bool(loop.run_until_complete(coro))
    finally:
        loop.close()

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


def _strip_stage_directions(text: str) -> str:
    """Remove parenthetical stage directions; return only spoken words."""
    stripped = re.sub(r"\([^)]*\)", "", text)
    return stripped.strip()


def _find_center_characters(script: str) -> set[str]:
    chars: set[str] = set()
    for m in re.finditer(r"<center>([^<]+)</center>", script):
        c = _clean_text(m.group(1))
        if c:
            chars.add(c.upper())
    return chars


def _find_colon_characters(script: str, min_dialogue: int = 5) -> set[str]:
    chars: set[str] = set()
    pattern = r"^[>\s]*\*{0,2}([A-Z][A-Za-z\s]+?)\*{0,2}\s*:\s*(.{" + str(min_dialogue) + r",})$"
    for m in re.finditer(pattern, script, re.MULTILINE):
        c = _clean_text(m.group(1))
        if c and len(c) >= 2:
            chars.add(c.upper())
    return chars


def _parse_dialogue_lines(script: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    center_chars = _find_center_characters(script)

    # Center-tag format: scan line-by-line so we can skip stage-direction-only lines
    # and find the first spoken line after each <center>CHARACTER</center> heading.
    script_lines = script.split("\n")
    for idx, raw_line in enumerate(script_lines):
        center_match = re.match(r"<center>([^<]+)</center>", raw_line.strip())
        if not center_match:
            continue
        char = _clean_text(center_match.group(1))
        # Look ahead through subsequent `>` lines; stop at blank line or new heading
        for j in range(idx + 1, len(script_lines)):
            candidate = script_lines[j].strip()
            if not candidate:
                break
            if re.match(r"<center>", candidate):
                break
            if candidate.startswith(">"):
                spoken = _strip_stage_directions(_clean_text(candidate))
                if spoken and len(spoken) > 5:
                    lines.append((char, spoken))
                    break

    valid_chars = center_chars or _find_colon_characters(script, 5)

    colon_re = r"^[>\s]*\*{0,2}([A-Z][A-Za-z\s]+?)\*{0,2}\s*:\s*(.+)$"
    colon_pattern = re.compile(colon_re, re.MULTILINE)
    for m in colon_pattern.finditer(script):
        char = _clean_text(m.group(1))
        dialogue = _strip_stage_directions(_clean_text(m.group(2)))
        if char and dialogue and len(dialogue) > 5:
            if valid_chars and char.upper() not in valid_chars:
                continue
            if not any(c == char and d == dialogue for c, d in lines):
                lines.append((char, dialogue))

    if not lines:
        for line in script.split("\n"):
            cleaned = _clean_text(line)
            skip = (
                line.startswith("**") or line.startswith("INT.")
                or line.startswith("EXT.") or line.startswith("<")
            )
            if cleaned and len(cleaned) > 15 and not skip:
                lines.append(("Narrator", cleaned))

    return lines


class VoiceSynthesisAgent:
    stage = StageType.AUDIO
    _agent: Agent | None = None

    def __init__(
        self,
        model: Model | None = None,
        providers: list[VoiceSynthesisProvider] | None = None,
    ) -> None:
        self._model = model
        self._providers = providers  # None → lazy-initialised in process()

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

    def _get_providers(self) -> list[VoiceSynthesisProvider]:
        if self._providers is not None:
            return self._providers
        # Default provider stack: ElevenLabs first, Piper fallback
        from holodeck.agents.audio.elevenlabs_provider import ElevenLabsProvider
        from holodeck.agents.audio.voice_provider import PiperProvider
        return [ElevenLabsProvider(), PiperProvider()]

    @observe(name="voice_synthesis.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        import os

        script = context.get("script", "")
        lines = _parse_dialogue_lines(script)

        media_dir = os.path.join(
            context.get("output_dir", "./output"),
            "media",
            str(context.get("production_id", "unknown")),
        )
        os.makedirs(media_dir, exist_ok=True)

        providers = self._get_providers()
        audio_urls: list[str] = []
        audio_metadata: list[dict] = []
        engines_used: set[str] = set()

        for i, (char, text) in enumerate(lines[:50]):
            fname = f"dialogue_{i:04d}_{char[:10].replace(' ', '_')}.mp3"
            output_path = os.path.join(media_dir, fname)

            handled = False
            for provider in providers:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    ok = pool.submit(
                        _run_provider_in_thread, provider, text, char, output_path, context
                    ).result()
                if ok:
                    audio_urls.append(output_path)
                    audio_metadata.append({"file": output_path, "character": char, "text": text})
                    engines_used.add(type(provider).__name__.removesuffix("Provider").lower())
                    handled = True
                    break

            if not handled:
                import logging
                logging.getLogger(__name__).warning(
                    "All providers failed for character '%s' line %d — skipping", char, i
                )

        tts_engine = ", ".join(sorted(engines_used)) if engines_used else "none"
        context["dialogue_audio_urls"] = audio_urls
        context["dialogue_audio_metadata"] = audio_metadata

        metadata_path = os.path.join(media_dir, "dialogue_metadata.json")
        with open(metadata_path, "w") as f:
            import json as _json
            _json.dump(audio_metadata, f, indent=2)
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
