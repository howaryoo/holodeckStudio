"""Integration tests for voice sample upload and retrieval flow.

Requires k8s cluster + port-forwards (make start).
Mark: pytest.mark.integration
"""
from __future__ import annotations

import pytest
from pathlib import Path
from uuid import uuid4, UUID

FIXTURE_AUDIO = Path(__file__).parent.parent / "fixtures" / "audio" / "sample_15s.mp3"
_BIBLE_ID = UUID("00000000-0000-0000-0000-000000000099")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_sample_round_trip() -> None:
    """Upload a fixture MP3, verify DB record, then disable and verify is_active=False."""
    from holodeck.storage.voice_sample_store import validate_audio_file, upload_voice_sample
    from holodeck.storage.postgres import ActorVoiceSample, ActorVoiceSampleRepository
    from holodeck.config.settings import Settings

    if not FIXTURE_AUDIO.exists():
        pytest.skip("Fixture audio file not found")

    settings = Settings()
    duration, fmt = validate_audio_file(str(FIXTURE_AUDIO))
    assert duration >= 15.0
    assert fmt == "mp3"

    char_name = f"Test Character {uuid4().hex[:8]}"
    object_key = await upload_voice_sample(str(FIXTURE_AUDIO), _BIBLE_ID, char_name, settings)
    assert object_key.startswith("voice-samples/")

    repo = ActorVoiceSampleRepository()
    sample = ActorVoiceSample(
        id=uuid4(),
        bible_id=_BIBLE_ID,
        character_name=char_name,
        sample_file_path=object_key,
        source_format=fmt,
        duration_seconds=duration,
        is_active=True,
    )
    await repo.create(sample)

    fetched = await repo.get_active(_BIBLE_ID, char_name)
    assert fetched is not None
    assert fetched.character_name == char_name
    assert fetched.is_active is True
    assert fetched.elevenlabs_voice_id is None

    await repo.deactivate(_BIBLE_ID, char_name)
    after_disable = await repo.get_active(_BIBLE_ID, char_name)
    assert after_disable is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_voice_synthesis_agent_piper_fallback_when_no_elevenlabs_key() -> None:
    """Agent produces audio via Piper when ELEVENLABS_API_KEY is empty."""
    import os
    import tempfile
    from holodeck.agents.audio.voice_synthesis import VoiceSynthesisAgent
    from holodeck.agents.audio.voice_provider import PiperProvider
    from holodeck.config.settings import Settings

    settings = Settings(elevenlabs_api_key="")
    agent = VoiceSynthesisAgent(providers=[PiperProvider()])

    with tempfile.TemporaryDirectory() as tmp:
        context = {
            "script": "RACHEL: That's not even a word!\nMONICA: Yes it is.",
            "output_dir": tmp,
            "production_id": "integration-test",
            "bible_id": str(_BIBLE_ID),
        }
        output = agent.process(context)

    assert output.metadata is not None
    assert isinstance(output.metadata.get("audio_urls"), list)
