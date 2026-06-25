"""Unit tests for ElevenLabsProvider voice cloning and synthesis paths."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from holodeck.agents.audio.elevenlabs_provider import ElevenLabsProvider
from holodeck.config.settings import Settings
from holodeck.storage.postgres import ActorVoiceSample, ActorVoiceSampleRepository

_BIBLE_ID = UUID("00000000-0000-0000-0000-000000000001")
_SAMPLE_ID = uuid4()
_VOICE_ID = "voice_abc123"


def _make_sample(voice_id: str | None = None) -> ActorVoiceSample:
    s = ActorVoiceSample()
    s.id = _SAMPLE_ID
    s.bible_id = _BIBLE_ID
    s.character_name = "Rachel Green"
    s.sample_file_path = f"voice-samples/{_BIBLE_ID}/rachel_green/sample.mp3"
    s.source_format = "mp3"
    s.duration_seconds = 30.0
    s.elevenlabs_voice_id = voice_id
    s.upload_date = datetime.utcnow()
    s.is_active = True
    return s


def _settings_with_key() -> Settings:
    return Settings(
        elevenlabs_api_key="sk_fake_key",
        elevenlabs_voice_model="eleven_monolingual_v1",
        elevenlabs_voice_stability=0.5,
        elevenlabs_similarity_boost=0.75,
        elevenlabs_use_speaker_boost=False,
    )


@pytest.mark.asyncio
async def test_returns_false_when_api_key_empty(tmp_path: pytest.TempPathFactory) -> None:
    provider = ElevenLabsProvider(settings=Settings(elevenlabs_api_key=""))
    result = await provider.synthesize(
        "Hello", "Rachel Green", str(tmp_path / "out.mp3"),
        {"bible_id": str(_BIBLE_ID), "production_id": "test"},
    )
    assert result is False


@pytest.mark.asyncio
async def test_returns_false_when_no_sample(tmp_path: pytest.TempPathFactory) -> None:
    mock_repo = AsyncMock(spec=ActorVoiceSampleRepository)
    mock_repo.get_active.return_value = None
    provider = ElevenLabsProvider(settings=_settings_with_key(), repository=mock_repo)
    result = await provider.synthesize(
        "Hello", "Rachel Green", str(tmp_path / "out.mp3"),
        {"bible_id": str(_BIBLE_ID), "production_id": "test"},
    )
    assert result is False
    mock_repo.get_active.assert_called_once_with(_BIBLE_ID, "Rachel Green")


@pytest.mark.asyncio
async def test_reuses_cached_voice_id(tmp_path: pytest.TempPathFactory) -> None:
    """When voice_id is already in DB, voices.add() must NOT be called."""
    mock_repo = AsyncMock(spec=ActorVoiceSampleRepository)
    mock_repo.get_active.return_value = _make_sample(voice_id=_VOICE_ID)

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = iter([b"fake_audio"])

    with patch("elevenlabs.client.ElevenLabs", return_value=mock_client):
        provider = ElevenLabsProvider(settings=_settings_with_key(), repository=mock_repo)
        output_path = str(tmp_path / "out.mp3")
        result = await provider.synthesize(
            "That's not even a word!", "Rachel Green", output_path,
            {"bible_id": str(_BIBLE_ID), "production_id": "test"},
        )

    assert result is True
    mock_client.voices.add.assert_not_called()
    mock_client.text_to_speech.convert.assert_called_once()
    assert (tmp_path / "out.mp3").read_bytes() == b"fake_audio"


@pytest.mark.asyncio
async def test_clones_voice_on_first_use_and_caches(tmp_path: pytest.TempPathFactory) -> None:
    """When voice_id is NULL, voices.ivc.create() is called and result persisted."""
    mock_repo = AsyncMock(spec=ActorVoiceSampleRepository)
    mock_repo.get_active.return_value = _make_sample(voice_id=None)
    mock_repo.update_voice_id = AsyncMock()

    mock_voice = MagicMock()
    mock_voice.voice_id = _VOICE_ID

    mock_client = MagicMock()
    mock_client.voices.ivc.create.return_value = mock_voice
    mock_client.text_to_speech.convert.return_value = iter([b"cloned_audio"])

    # Patch MinIO store used inside _clone_voice
    mock_store = AsyncMock()
    mock_store.get.return_value = b"sample_bytes"

    with patch("elevenlabs.client.ElevenLabs", return_value=mock_client), \
         patch("holodeck.storage.object_store.MinIOObjectStore", return_value=mock_store):
        provider = ElevenLabsProvider(settings=_settings_with_key(), repository=mock_repo)
        result = await provider.synthesize(
            "We were on a break!", "Rachel Green", str(tmp_path / "out.mp3"),
            {"bible_id": str(_BIBLE_ID), "production_id": "test"},
        )

    assert result is True
    mock_client.voices.ivc.create.assert_called_once()
    mock_repo.update_voice_id.assert_called_once_with(_SAMPLE_ID, _VOICE_ID)


@pytest.mark.asyncio
async def test_returns_false_not_raises_on_api_error(tmp_path: pytest.TempPathFactory) -> None:
    """Any SDK exception must be caught; provider returns False, not raises."""
    mock_repo = AsyncMock(spec=ActorVoiceSampleRepository)
    mock_repo.get_active.return_value = _make_sample(voice_id=_VOICE_ID)

    mock_client = MagicMock()
    mock_client.text_to_speech.convert.side_effect = RuntimeError("API down")

    with patch("elevenlabs.client.ElevenLabs", return_value=mock_client):
        provider = ElevenLabsProvider(settings=_settings_with_key(), repository=mock_repo)
        result = await provider.synthesize(
            "Hello", "Rachel Green", str(tmp_path / "out.mp3"),
            {"bible_id": str(_BIBLE_ID), "production_id": "test"},
        )

    assert result is False
