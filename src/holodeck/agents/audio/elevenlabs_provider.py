from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from holodeck.config.settings import Settings
from holodeck.storage.postgres import ActorVoiceSampleRepository

logger = logging.getLogger(__name__)


class ElevenLabsProvider:
    """VoiceSynthesisProvider that generates character-cloned audio via the ElevenLabs API.

    On first use per character, calls client.voices.add() to clone the voice from the stored
    sample and caches the voice_id in the database.  Subsequent calls reuse the cached id.

    Returns False (no exception) when:
    - ELEVENLABS_API_KEY is empty
    - No active ActorVoiceSample exists for the character
    - Any ElevenLabs SDK exception occurs (logged at WARNING; caller falls back to Piper)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        repository: ActorVoiceSampleRepository | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._repo = repository or ActorVoiceSampleRepository()

    async def synthesize(
        self,
        text: str,
        char_name: str,
        output_path: str,
        context: dict,
    ) -> bool:
        if not self._settings.elevenlabs_api_key:
            return False

        raw_bible_id = context.get("bible_id")
        if raw_bible_id is None:
            return False
        try:
            bible_id = UUID(str(raw_bible_id))
        except (ValueError, AttributeError):
            logger.warning(
                "ElevenLabsProvider: invalid bible_id '%s' — skipping voice clone",
                raw_bible_id,
            )
            return False

        sample = await self._repo.get_active(bible_id, char_name)
        if sample is None:
            return False

        try:
            from elevenlabs import VoiceSettings
            from elevenlabs.client import ElevenLabs

            client = ElevenLabs(api_key=self._settings.elevenlabs_api_key)

            voice_id = sample.elevenlabs_voice_id
            if not voice_id:
                voice_id = await self._clone_voice(
                    client, sample.character_name, sample.sample_file_path
                )
                await self._repo.update_voice_id(sample.id, voice_id)

            audio_chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self._settings.elevenlabs_voice_model,
                voice_settings=VoiceSettings(
                    stability=self._settings.elevenlabs_voice_stability,
                    similarity_boost=self._settings.elevenlabs_similarity_boost,
                    use_speaker_boost=self._settings.elevenlabs_use_speaker_boost,
                ),
            )
            audio_bytes = b"".join(audio_chunks)
            Path(output_path).write_bytes(audio_bytes)
            logger.info(
                "ElevenLabsProvider: synthesized %d bytes for %s → %s",
                len(audio_bytes),
                char_name,
                output_path,
            )
            return True

        except Exception as exc:
            logger.warning(
                "ElevenLabsProvider: API error for character '%s': %s — falling back",
                char_name,
                exc,
            )
            return False

    async def _clone_voice(
        self,
        client: object,
        character_name: str,
        sample_file_path: str,
    ) -> str:
        """Clone a voice from a MinIO-stored sample file.

        Downloads the sample to a temp file, calls client.voices.add(), returns voice_id.
        """
        import contextlib
        import os
        import tempfile

        from holodeck.storage.object_store import MinIOObjectStore

        cfg = self._settings
        store = MinIOObjectStore(
            endpoint=cfg.minio_endpoint,
            access_key=cfg.minio_access_key,
            secret_key=cfg.minio_secret_key,
            secure=cfg.minio_secure,
        )

        ext = sample_file_path.rsplit(".", 1)[-1] if "." in sample_file_path else "mp3"
        audio_data = await store.get(cfg.minio_bucket, sample_file_path)

        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as audio_file:
                voice = client.voices.ivc.create(  # type: ignore[attr-defined]
                    name=character_name,
                    description=f"Voice clone for {character_name} — HolodeckStudio",
                    files=[("sample.mp3", audio_file, "audio/mpeg")],
                )
            return voice.voice_id
        finally:
            with contextlib.suppress(OSError):
                os.remove(tmp_path)
