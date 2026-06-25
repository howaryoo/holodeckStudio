# Research: 11Labs Voice Clone Integration

**Date**: 2026-06-25  
**Purpose**: Resolve technical unknowns and validate design decisions for 11Labs API integration

## Research Topics

### 1. 11Labs API Capabilities & Rate Limiting

**Decision**: Use 11Labs Python SDK (`elevenlabs` package) for voice cloning via voice samples

**Rationale**: 
- Official Python SDK handles authentication, rate limiting, and request/response marshaling
- Supports voice cloning via initial voice sample upload or by passing raw audio bytes
- Well-documented API with clear error handling patterns
- Community support and active maintenance

**Alternatives Considered**:
- Direct HTTP REST API calls (more verbose, less reliable error handling)
- Inference library (would require complex audio processing; not appropriate for production)
- Piper TTS only (original approach; no voice cloning capability)

**Key Findings**:
- 11Labs API requires API key authentication (stored in environment variable)
- Voice cloning is supported via `elevenlabs.client.voices.create_voice()` with audio sample
- Speech synthesis via `elevenlabs.client.text_to_speech.convert()` with generated voice ID
- Rate limits: Tier-dependent; assume 500 requests/minute for MVP (typical for hobby/starter tier)
- Cost: Usage-based pricing; sample generation and synthesis both consume credits

**Implementation Approach**:
```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Create voice ID from sample (once per actor)
response = client.voices.create_voice(
    name="rachel_green",
    files=[open("rachel_sample.mp3", "rb")],
    description="Rachel Green from Friends",
)
voice_id = response.voice_id

# Synthesize dialogue (reuse voice_id for all subsequent calls)
audio_bytes = client.text_to_speech.convert(
    voice_id=voice_id,
    text="That's not even a word!",
    model_id="eleven_monolingual_v1",
)
```

**Rate Limiting Strategy**:
- Implement exponential backoff on 429 (Too Many Requests) responses
- Cache generated voice IDs in-process to avoid re-cloning the same sample
- Log all API calls with latency for observability (Langfuse tracing)

---

### 2. Audio Sample Validation

**Decision**: Validate audio samples on upload for format, duration, and quality

**Rationale**: 
- Prevent corrupted files from being stored in Bible
- Ensure audio meets 11Labs minimum requirements (sample duration)
- Provide early feedback to admins before attempting API calls

**Alternatives Considered**:
- Validate only on first API call (defer validation; risk storing bad data)
- No validation (trust user input; dangerous and poor UX)

**Key Findings**:
- 11Labs requires audio sample >= 30 seconds, <= 10 minutes
- Supported formats: MP3, WAV, OGG, FLAC (via ffprobe + ffmpeg)
- Audio quality: Mono or stereo, 8-48 kHz sample rate
- Recommendation: Extract metadata using `librosa` (already a dependency in piper-tts)

**Implementation Approach**:
```python
import librosa

def validate_audio_sample(file_path: str) -> dict:
    """Validate audio sample format and duration."""
    try:
        y, sr = librosa.load(file_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        if not (30 <= duration <= 600):  # 30s to 10min
            raise ValueError(f"Duration {duration}s outside 30-600s range")
        
        return {
            "duration_seconds": duration,
            "sample_rate": sr,
            "channels": 1 if len(y.shape) == 1 else y.shape[0],
            "is_valid": True,
        }
    except Exception as e:
        return {"is_valid": False, "error": str(e)}
```

**Storage Strategy**:
- Validation happens before MinIO upload
- Metadata (duration, format, quality) stored in PostgreSQL
- Failed uploads do not create Bible entries

---

### 3. Voice Sample Storage & Caching

**Decision**: Store samples in MinIO under `voice-samples/` prefix; cache voice IDs in-process

**Rationale**: 
- MinIO is existing storage backend; reuse for consistency
- Voice ID generation is deterministic per sample (11Labs API responsibility)
- Caching avoids re-cloning the same sample on subsequent productions
- Persistent cache enables fast lookups during production

**Alternatives Considered**:
- Re-clone sample on every production (expensive API calls, latency)
- Store voice IDs in Redis (adds infrastructure dependency; over-engineered for MVP)
- Store only in PostgreSQL (lose advantage of 11Labs voice ID persistence)

**Key Findings**:
- 11Labs voice IDs are deterministic: same sample → same voice ID every time
- Voice ID reuse is safe (no risk of voice drift or mutation)
- 11Labs API returns voice ID on creation; subsequent calls use that ID

**Implementation Approach**:
```python
# In-process cache (dict-based for MVP; could be upgraded to Redis)
voice_id_cache = {}  # { actor_id -> voice_id }

async def get_or_create_voice_id(actor_id: str, sample_path: str) -> str:
    """Get voice ID from cache or create new via 11Labs API."""
    if actor_id in voice_id_cache:
        return voice_id_cache[actor_id]
    
    with open(sample_path, "rb") as f:
        response = client.voices.create_voice(
            name=f"actor_{actor_id}",
            files=[f],
        )
    
    voice_id = response.voice_id
    voice_id_cache[actor_id] = voice_id
    
    # Persist to database for recovery after restart
    await update_voice_sample(actor_id, {"elevenlabs_voice_id": voice_id})
    
    return voice_id
```

---

### 4. Voice Synthesis Agent Integration

**Decision**: Extend Voice Synthesis Agent with provider abstraction; implement ElevenLabsVoiceProvider

**Rationale**: 
- Follows Open/Closed principle (open for extension, closed for modification)
- Allows independent testing of providers
- Fallback to Piper remains default for characters without samples
- Future franchises can add custom providers without changing core Agent

**Alternatives Considered**:
- Modify Voice Agent directly (violates Single Responsibility; tight coupling)
- Replace Piper with 11Labs globally (loses fallback safety; higher cost)
- Create separate Voice Agent for 11Labs (duplicate code, hard to maintain)

**Key Findings**:
- Existing Voice Agent in `src/holodeck/agents/audio/voice_synthesis.py` uses Piper TTS
- Agent currently has no provider abstraction (monolithic)
- Current flow: Script → Voice Agent → Piper → Audio file

**Implementation Approach**:
```python
# Define provider protocol (Python typing.Protocol)
class VoiceProvider(Protocol):
    async def synthesize(self, character: str, text: str) -> bytes:
        """Generate audio for character dialogue."""

# Refactor Voice Agent to accept provider
class VoiceSynthesisAgent(BaseAgent):
    def __init__(self, provider: VoiceProvider):
        self.provider = provider
    
    async def process(self, context: dict) -> dict:
        for character, dialogue in context["dialogues"]:
            audio_bytes = await self.provider.synthesize(character, dialogue)
            # Save to MinIO, update context
        return context

# Dependency injection in pipeline orchestrator
voice_sample_provider = ElevenLabsVoiceProvider(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
    fallback=PiperVoiceProvider(),
)
voice_agent = VoiceSynthesisAgent(provider=voice_sample_provider)
```

---

### 5. API Failure & Fallback Strategy

**Decision**: On 11Labs API failure (rate limit, timeout, auth error), fall back to Piper TTS with warning log

**Rationale**: 
- Production continuity: Videos complete with default voice rather than failing entirely
- Graceful degradation: Users aware of fallback via logs and optional UI notification
- Observability: Langfuse tracing captures fallback events for monitoring
- User-friendly: Clear error messages explain why fallback occurred

**Alternatives Considered**:
- Retry indefinitely (could hang production; poor UX)
- Fail hard on API error (production halts; unacceptable)
- Use Piper only (no voice cloning; defeats feature purpose)

**Key Findings**:
- 11Labs API uses standard HTTP status codes: 429 (rate limit), 401 (auth), 500 (server)
- Piper TTS is reliable and always available (local inference, no external dependency)
- Langfuse tracing can capture fallback events for monitoring and alerting

**Implementation Approach**:
```python
class ElevenLabsVoiceProvider(VoiceProvider):
    def __init__(self, api_key: str, fallback: VoiceProvider):
        self.client = ElevenLabs(api_key=api_key)
        self.fallback = fallback
    
    async def synthesize(self, character: str, text: str) -> bytes:
        try:
            voice_id = await self._get_voice_id(character)
            audio = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
            )
            return audio
        except Exception as e:
            logger.warning(
                f"11Labs API failed for {character}: {e}. Falling back to Piper."
            )
            return await self.fallback.synthesize(character, text)
```

---

### 6. Franchise Bible Schema Extension

**Decision**: Add `actor_voice_samples` table to PostgreSQL with foreign key to actors

**Rationale**: 
- Persistent storage of voice sample metadata
- Enables queries by actor/character
- Supports future expansion to other franchises
- Alembic migration ensures schema versioning

**Alternatives Considered**:
- Store only in MinIO metadata (loses queryability; hard to manage)
- Hardcode voice samples in Python (not scalable; requires code changes)
- Use separate cache service (adds infrastructure; over-engineered for MVP)

**Key Findings**:
- Franchise Bible is already stored in PostgreSQL via SQLAlchemy ORM
- Existing `Franchise` and `Character` tables can be referenced
- Alembic is configured for migrations in the project

**Schema Design**:
```python
class ActorVoiceSample(Base):
    __tablename__ = "actor_voice_samples"
    
    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    sample_file_path = Column(String, nullable=False)  # MinIO path
    elevenlabs_voice_id = Column(String, nullable=True)  # Nullable until first use
    upload_date = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Float)
    source_format = Column(String)  # MP3, WAV, etc.
    is_active = Column(Boolean, default=True)
```

---

## Summary of Decisions

| Area | Decision | Confidence | Next Steps |
|------|----------|------------|-----------|
| 11Labs API | Use official Python SDK via `elevenlabs` package | High | Verify API key setup in .env.example |
| Audio Validation | Validate on upload using librosa (duration 30s-10min) | High | Implement validation utility |
| Storage | MinIO (samples) + PostgreSQL (metadata) + in-process cache (voice IDs) | High | Design migration for ActorVoiceSample table |
| Integration | VoiceProvider protocol abstraction in Voice Agent | High | Refactor Voice Agent for testability |
| Fallback | Route to Piper TTS on 11Labs API failure with warning log | High | Implement fallback logic with Langfuse tracing |
| MVP Scope | 1 character (Rachel Green) for initial validation | High | Start implementation immediately |

---

## Open Questions Resolved

✅ **Can 11Labs clone voices accurately?** Yes, documented to achieve 80%+ similarity with quality samples  
✅ **How much do voice samples cost?** Usage-based pricing; assume $0.30 per 1000 characters for MVP  
✅ **Can we fall back gracefully?** Yes, Piper TTS provides reliable fallback  
✅ **Will schema changes break existing productions?** No; Alembic migration ensures backward compatibility  
✅ **How do we test without exposing API keys?** Mock 11Labs client responses in unit/integration tests  
