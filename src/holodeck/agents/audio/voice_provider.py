from __future__ import annotations

import contextlib
import logging
import os
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class VoiceSynthesisProvider(Protocol):
    """Protocol for voice synthesis backends.

    synthesize() writes an MP3 to output_path and returns True on success.
    Returning False means "I cannot handle this request" — the caller tries the next provider.
    Exceptions are reserved for unrecoverable local errors (disk full, bad path, etc.).
    API errors MUST be caught internally and return False.
    """

    async def synthesize(
        self,
        text: str,
        char_name: str,
        output_path: str,
        context: dict,
    ) -> bool: ...


class PiperProvider:
    """VoiceSynthesisProvider backed by local Piper TTS inference.

    Wraps the private helpers in voice_synthesis.py without modifying them.
    Falls through to gTTS if Piper models are not installed.
    """

    async def synthesize(
        self,
        text: str,
        char_name: str,
        output_path: str,
        context: dict,
    ) -> bool:
        from holodeck.agents.audio.voice_synthesis import (
            _get_piper_model_path,
            _has_gtts,
            _has_piper,
            _synthesize_with_piper,
            _wav_to_mp3,
        )

        character_visuals: dict = context.get("character_visuals", {})
        cv = character_visuals.get(char_name, {})
        voice_model = cv.get("voice_model", "")
        gender = "female" if voice_model.lower() in ("female", "f") else "male"

        if _has_piper():
            model_path = _get_piper_model_path(gender)
            wav_path = output_path.replace(".mp3", ".wav")
            try:
                if _synthesize_with_piper(text, model_path, wav_path):
                    if _wav_to_mp3(wav_path, output_path):
                        with contextlib.suppress(OSError):
                            os.remove(wav_path)
                        return True
                    # ffmpeg conversion failed but WAV exists — rename
                    os.replace(wav_path, output_path)
                    return True
            except Exception as exc:
                logger.warning("PiperProvider: synthesis error for %s: %s", char_name, exc)

        if _has_gtts():
            try:
                from gtts import gTTS
                tts = gTTS(text=text, lang="en", tld="com", slow=False)
                tts.save(output_path)
                return True
            except Exception as exc:
                logger.warning("PiperProvider (gTTS fallback): error for %s: %s", char_name, exc)

        return False
