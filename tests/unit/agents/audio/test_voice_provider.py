"""Unit tests for VoiceSynthesisProvider Protocol and PiperProvider."""
from __future__ import annotations

import pytest

from holodeck.agents.audio.elevenlabs_provider import ElevenLabsProvider
from holodeck.agents.audio.voice_provider import PiperProvider, VoiceSynthesisProvider


def test_piper_provider_satisfies_protocol() -> None:
    assert isinstance(PiperProvider(), VoiceSynthesisProvider)


def test_elevenlabs_provider_satisfies_protocol() -> None:
    assert isinstance(ElevenLabsProvider(), VoiceSynthesisProvider)


@pytest.mark.asyncio
async def test_piper_provider_returns_bool(tmp_path: pytest.TempPathFactory) -> None:
    provider = PiperProvider()
    output = str(tmp_path / "out.mp3")
    result = await provider.synthesize(
        text="Hello world",
        char_name="Test",
        output_path=output,
        context={},
    )
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_elevenlabs_provider_returns_false_when_no_api_key(
    tmp_path: pytest.TempPathFactory,
) -> None:
    from holodeck.config.settings import Settings
    settings = Settings(elevenlabs_api_key="")
    provider = ElevenLabsProvider(settings=settings)
    result = await provider.synthesize(
        text="Hello",
        char_name="Rachel Green",
        output_path=str(tmp_path / "out.mp3"),
        context={"bible_id": "00000000-0000-0000-0000-000000000001", "production_id": "test"},
    )
    assert result is False


@pytest.mark.asyncio
async def test_elevenlabs_provider_returns_false_when_no_sample(
    tmp_path: pytest.TempPathFactory,
) -> None:
    from unittest.mock import AsyncMock

    from holodeck.config.settings import Settings
    from holodeck.storage.postgres import ActorVoiceSampleRepository

    settings = Settings(elevenlabs_api_key="sk_fake_key")
    mock_repo = AsyncMock(spec=ActorVoiceSampleRepository)
    mock_repo.get_active.return_value = None

    provider = ElevenLabsProvider(settings=settings, repository=mock_repo)
    result = await provider.synthesize(
        text="Hello",
        char_name="Unknown Character",
        output_path=str(tmp_path / "out.mp3"),
        context={"bible_id": "00000000-0000-0000-0000-000000000001", "production_id": "test"},
    )
    assert result is False
    mock_repo.get_active.assert_called_once()
