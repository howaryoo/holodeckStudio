# Contract: VoiceProvider Interface

**Date**: 2026-06-25  
**Purpose**: Define the interface contract for voice providers (11Labs, Piper, etc.)

## Overview

The `VoiceProvider` is a protocol that defines how voice synthesis providers must behave. This contract enables:
- Multiple provider implementations (11Labs, Piper, future providers)
- Easy testing via mock providers
- Provider-agnostic Voice Synthesis Agent
- Safe provider substitution and composition

---

## VoiceProvider Protocol

```python
from typing import Protocol
from abc import abstractmethod

class VoiceProvider(Protocol):
    """
    Protocol for voice synthesis providers.
    
    Any implementation that follows this contract can be used
    with the Voice Synthesis Agent.
    """
    
    async def synthesize(
        self,
        character_name: str,
        text: str,
        **kwargs,
    ) -> bytes:
        """
        Synthesize dialogue text into audio bytes.
        
        Args:
            character_name (str): Character identifier (e.g., "Rachel Green", "rachel_green")
            text (str): Dialogue text to synthesize
            **kwargs: Provider-specific options (model, speed, etc.)
        
        Returns:
            bytes: Audio content (MP3 or WAV format, per provider default)
        
        Raises:
            VoiceProviderError: If synthesis fails (API error, invalid character, etc.)
        
        Behavior:
            - MUST be async (use in concurrent production pipelines)
            - MUST return audio bytes immediately (no streaming)
            - MUST fall back gracefully if the provider fails
            - MUST log synthesis attempts (for observability)
            - SHOULD handle provider-specific errors (rate limits, auth) with clear messages
        """
        ...
```

---

## Exceptions & Error Handling

### VoiceProviderError (Base Exception)

```python
class VoiceProviderError(Exception):
    """Base exception for voice provider errors."""
    def __init__(
        self,
        message: str,
        provider: str,
        character: str,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.provider = provider
        self.character = character
        self.original_error = original_error
        super().__init__(self.message)
```

### Specific Error Types

```python
class CharacterNotFoundError(VoiceProviderError):
    """Raised when character has no voice sample stored."""
    pass

class ProviderAPIError(VoiceProviderError):
    """Raised when provider API call fails (timeout, 5xx, etc.)."""
    pass

class RateLimitError(VoiceProviderError):
    """Raised when provider rate limit is exceeded."""
    pass

class AuthenticationError(VoiceProviderError):
    """Raised when API key is invalid or missing."""
    pass

class InvalidAudioError(VoiceProviderError):
    """Raised when audio synthesis produces invalid/empty data."""
    pass
```

---

## Implementation Requirements

### ElevenLabsVoiceProvider

**Implements**: `VoiceProvider` protocol

**Responsibilities**:
1. Load API key from `ELEVENLABS_API_KEY` environment variable
2. Retrieve voice sample metadata from Franchise Bible (character_id → ActorVoiceSample)
3. Generate or retrieve voice ID from 11Labs API via `get_or_create_voice_id()`
4. Call 11Labs `text_to_speech.convert()` with configured parameters
5. Handle API errors with exponential backoff and fallback
6. Emit Langfuse events for tracing and monitoring

**Configuration Parameters**:
```python
class ElevenLabsVoiceProvider:
    def __init__(
        self,
        api_key: str,
        model_id: str = "eleven_monolingual_v1",
        voice_stability: float = 0.5,
        similarity_boost: float = 0.75,
        use_speaker_boost: bool = False,
        fallback_provider: VoiceProvider = None,
        max_retries: int = 3,
    ):
        ...
```

**Example Usage**:
```python
provider = ElevenLabsVoiceProvider(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    fallback_provider=PiperVoiceProvider(),
)

audio_bytes = await provider.synthesize("Rachel Green", "That's not even a word!")
```

### PiperVoiceProvider

**Implements**: `VoiceProvider` protocol

**Responsibilities**:
1. Use existing Piper TTS models (already in project)
2. Map character names to Piper voice models (or use default)
3. Generate audio via Piper inference
4. No external API calls (always reliable)

**Configuration Parameters**:
```python
class PiperVoiceProvider:
    def __init__(
        self,
        character_voice_map: Dict[str, str] = None,
        default_voice: str = "en_US-libritts-high",
    ):
        ...
```

**Behavior**:
- No external dependencies
- Synchronous inference (wrapped as async for interface consistency)
- Always succeeds (no error handling needed, unless model loading fails)

---

## Composition & Fallback

### Fallback Pattern

The 11Labs provider can wrap a fallback provider to ensure graceful degradation:

```python
class FallbackVoiceProvider:
    """Wraps primary provider with fallback on failure."""
    
    def __init__(
        self,
        primary: VoiceProvider,
        fallback: VoiceProvider,
        enable_logging: bool = True,
    ):
        self.primary = primary
        self.fallback = fallback
        self.enable_logging = enable_logging
    
    async def synthesize(
        self,
        character_name: str,
        text: str,
        **kwargs,
    ) -> bytes:
        try:
            return await self.primary.synthesize(character_name, text, **kwargs)
        except Exception as e:
            if self.enable_logging:
                logger.warning(
                    f"Primary provider failed for {character_name}: {e}. "
                    f"Falling back to {self.fallback.__class__.__name__}."
                )
            return await self.fallback.synthesize(character_name, text, **kwargs)
```

### Composition Example

```python
# Build provider stack
piper_provider = PiperVoiceProvider()
elevenlabs_provider = ElevenLabsVoiceProvider(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# Wrap with fallback
voice_provider = FallbackVoiceProvider(
    primary=elevenlabs_provider,
    fallback=piper_provider,
    enable_logging=True,
)

# Use in Voice Synthesis Agent
voice_agent = VoiceSynthesisAgent(provider=voice_provider)
```

---

## Testing Contract

### Mock Provider for Unit Tests

```python
class MockVoiceProvider(VoiceProvider):
    """Mock provider for testing."""
    
    def __init__(self, return_audio: bytes = b"fake_audio"):
        self.return_audio = return_audio
        self.calls = []  # Track calls for assertions
    
    async def synthesize(
        self,
        character_name: str,
        text: str,
        **kwargs,
    ) -> bytes:
        self.calls.append({
            "character": character_name,
            "text": text,
            "kwargs": kwargs,
        })
        return self.return_audio
```

### Contract Compliance Tests

Every provider implementation MUST pass:

```python
async def test_provider_synthesize_returns_bytes():
    """Provider.synthesize() returns bytes."""
    provider = MyVoiceProvider()
    result = await provider.synthesize("TestChar", "Hello world")
    assert isinstance(result, bytes)
    assert len(result) > 0

async def test_provider_handles_invalid_character():
    """Provider raises CharacterNotFoundError for unknown character."""
    provider = MyVoiceProvider()
    with pytest.raises(CharacterNotFoundError):
        await provider.synthesize("UnknownChar", "Hello")

async def test_provider_async_interface():
    """Provider.synthesize() is async."""
    provider = MyVoiceProvider()
    result = provider.synthesize("TestChar", "Hello")
    assert asyncio.iscoroutine(result) or asyncio.isfuture(result)
    audio = await result
    assert isinstance(audio, bytes)
```

---

## Observability & Logging

All providers MUST emit the following events via Langfuse/structlog:

```python
# Before synthesis attempt
logger.info(
    "voice_synthesis_start",
    character=character_name,
    text_length=len(text),
    provider=self.__class__.__name__,
)

# On success
logger.info(
    "voice_synthesis_success",
    character=character_name,
    audio_size_bytes=len(audio_bytes),
    latency_ms=elapsed_ms,
    provider=self.__class__.__name__,
)

# On failure
logger.error(
    "voice_synthesis_failed",
    character=character_name,
    error=str(e),
    provider=self.__class__.__name__,
    latency_ms=elapsed_ms,
)
```

---

## Evolution & Versioning

### Adding New Provider

1. Create new class implementing `VoiceProvider` protocol
2. Pass all contract compliance tests
3. Update Voice Synthesis Agent to expose provider as configuration option
4. Document provider-specific configuration in CLAUDE.md

### Changing Interface

Contract changes (adding/removing methods) require:
1. All existing providers updated to implement new interface
2. Tests updated
3. Documentation updated
4. Migration plan for existing productions (if breaking change)

---

## Summary Table

| Aspect | Requirement |
|--------|-------------|
| **Async** | MUST be async (`async def`) |
| **Input** | character_name: str, text: str, **kwargs |
| **Output** | bytes (audio content) |
| **Errors** | Raise VoiceProviderError or subclass |
| **Logging** | Emit structured logs for observability |
| **Fallback** | Graceful error handling with fallback option |
| **Caching** | Provider may cache voice IDs internally |
| **Testing** | Must pass contract compliance tests |
