# Contract: VoiceSynthesisProvider Interface

**Date**: 2026-06-25
**Purpose**: Define the Protocol contract for voice synthesis backends

---

## VoiceSynthesisProvider Protocol

```python
# src/holodeck/agents/audio/voice_provider.py

from typing import Protocol, runtime_checkable

@runtime_checkable
class VoiceSynthesisProvider(Protocol):
    """
    Protocol for voice synthesis backends.

    synthesize() writes an MP3 file to output_path and returns True on success.
    Returning False signals "I cannot handle this request" — the agent tries the next provider.
    Raising an exception is reserved for unrecoverable errors (e.g., disk full).
    """

    async def synthesize(
        self,
        text: str,
        char_name: str,
        output_path: str,
        context: dict,
    ) -> bool:
        """
        Args:
            text:        Dialogue text to synthesize.
            char_name:   Character display name (e.g., "Rachel Green").
            output_path: Absolute path where the resulting MP3 must be written.
            context:     Pipeline context dict; must contain at minimum:
                         - "bible_id" (str | UUID): franchise bible identifier.
                         - "production_id" (str): current production identifier.

        Returns:
            True  — MP3 written to output_path successfully.
            False — Provider cannot handle this (no sample, no key, API unavailable).
                    Agent will try the next provider in its list.

        Raises:
            Exception — Only on unrecoverable local errors (e.g., disk full, bad output_path).
                        API errors MUST be caught internally and return False instead.
        """
        ...
```

---

## Selection Logic in VoiceSynthesisAgent

```python
for provider in self._providers:
    if await provider.synthesize(text, char_name, output_path, context):
        break   # first provider that succeeds wins
else:
    logger.warning("All providers returned False for %s — skipping line", char_name)
```

Default provider list (when no `providers` arg given):
```
[ElevenLabsProvider, PiperProvider]
```
When `ELEVENLABS_API_KEY` is empty, `ElevenLabsProvider.synthesize()` returns `False` immediately
so `PiperProvider` handles all characters (backward-compatible with existing behavior).

---

## Concrete Implementations

### ElevenLabsProvider

| Attribute | Value |
|-----------|-------|
| Returns `False` when | API key empty, no active voice sample for character, any SDK exception |
| Raises | `KeyError` if `context["bible_id"]` is absent |
| Side effects | Calls `client.voices.add()` once per sample (caches voice_id in DB) |
| Observability | `logger.warning(...)` on fallback; all SDK errors logged at WARNING |

### PiperProvider

| Attribute | Value |
|-----------|-------|
| Returns `False` when | Piper models not installed, synthesis subprocess fails |
| Raises | Never — all errors caught internally |
| Side effects | Writes WAV then converts to MP3 via ffmpeg; deletes intermediate WAV |
| Observability | No external calls; failure is local subprocess error |

---

## Protocol Compliance Tests

Every concrete implementation must pass:

```python
from holodeck.agents.audio.voice_provider import VoiceSynthesisProvider

def test_satisfies_protocol(provider):
    assert isinstance(provider, VoiceSynthesisProvider)

async def test_returns_bool(provider, tmp_path):
    result = await provider.synthesize(
        text="Hello world",
        char_name="Test Character",
        output_path=str(tmp_path / "out.mp3"),
        context={"bible_id": "test-bible", "production_id": "test-prod"},
    )
    assert isinstance(result, bool)

async def test_returns_false_not_raises_on_api_error(provider_with_bad_key, tmp_path):
    """API errors must become False, not exceptions."""
    result = await provider_with_bad_key.synthesize(
        text="Hello",
        char_name="Rachel Green",
        output_path=str(tmp_path / "out.mp3"),
        context={"bible_id": "x", "production_id": "y"},
    )
    assert result is False
```
