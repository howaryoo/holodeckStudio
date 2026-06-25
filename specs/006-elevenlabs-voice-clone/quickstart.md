# Quickstart: 11Labs Voice Clone Integration

**Date**: 2026-06-25  
**Audience**: Developers and admins setting up voice cloning for a new franchise or character

---

## 5-Minute Setup

### 1. Get API Key

1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Generate API key from account settings
3. Add to `.env`:
```bash
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_API_RATE_LIMIT=500  # requests per minute
ELEVENLABS_MODEL_ID=eleven_monolingual_v1
ELEVENLABS_VOICE_STABILITY=0.5
ELEVENLABS_SIMILARITY_BOOST=0.75
```

### 2. Start the Cluster

```bash
make start  # PostgreSQL + MinIO + k8s cluster
uv run alembic upgrade head  # Apply schema migrations (includes ActorVoiceSample table)
```

### 3. Test Voice Cloning

```bash
# Upload a voice sample for Rachel Green
uv run python -m holodeck.cli bible add-voice-sample \
  --franchise "Friends" \
  --character "Rachel Green" \
  --sample-file ~/rachel_sample.mp3

# Generate dialogue with voice clone
uv run python -m holodeck.cli produce \
  "Rachel Green sits in Central Perk..." \
  --bible friends \
  --character-voice rachel_green
```

---

## Detailed Setup

### Step 1: Prepare Voice Sample

A voice sample should:
- **Duration**: 30–600 seconds (11Labs requirement)
- **Quality**: Clear audio, minimal background noise, consistent volume
- **Format**: MP3, WAV, OGG, or FLAC
- **Speaker**: Native English speaker (for `eleven_monolingual_v1` model)

**Recommended**: Use a 1–3 minute clip from existing TV dialogue (e.g., a Friends episode scene).

### Step 2: Add Sample to Franchise Bible

Use the Bible management CLI:

```bash
uv run python -m holodeck.cli bible add-voice-sample \
  --franchise "Friends" \
  --character "Rachel Green" \
  --sample-file /path/to/rachel_sample.mp3 \
  --description "Rachel Green from Friends S01E01"
```

**What happens**:
1. Sample is validated (format, duration, quality checks)
2. File is uploaded to MinIO under `voice-samples/rachel_green/sample.mp3`
3. Metadata is stored in PostgreSQL (`actor_voice_samples` table)
4. System is ready for first use

### Step 3: Generate Scripts with Voice Cloning

Modify the production pipeline to use voice cloning for characters with stored samples:

```python
# In your production script
from holodeck.agents.audio.providers import ElevenLabsVoiceProvider, PiperVoiceProvider, FallbackVoiceProvider
from holodeck.agents.audio.voice_synthesis import VoiceSynthesisAgent

# Create provider stack
piper_provider = PiperVoiceProvider()
elevenlabs_provider = ElevenLabsVoiceProvider(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

voice_provider = FallbackVoiceProvider(
    primary=elevenlabs_provider,
    fallback=piper_provider,
)

# Use in Voice Synthesis Agent
voice_agent = VoiceSynthesisAgent(provider=voice_provider)

# Run production
result = await orchestrator.run([voice_agent, ...])
```

---

## Common Tasks

### Query Stored Voice Samples

```bash
# List all voice samples for Friends
uv run python -m holodeck.cli bible list-voice-samples --franchise "Friends"

# Get metadata for Rachel Green's sample
uv run python -m holodeck.cli bible get-voice-sample "rachel_green"
```

### Update Voice Sample

Replace an existing voice sample:

```bash
uv run python -m holodeck.cli bible update-voice-sample \
  --character "Rachel Green" \
  --sample-file /path/to/new_sample.mp3 \
  --description "Rachel Green v2 - improved audio quality"
```

### Disable Voice Cloning Temporarily

```bash
# Disable voice sample without deleting
uv run python -m holodeck.cli bible disable-voice-sample "rachel_green"

# Production will fall back to Piper TTS for this character
# To re-enable:
uv run python -m holodeck.cli bible enable-voice-sample "rachel_green"
```

### Add More Characters

Repeat Step 2 for each character:

```bash
# Monica
uv run python -m holodeck.cli bible add-voice-sample \
  --franchise "Friends" \
  --character "Monica Geller" \
  --sample-file ~/monica_sample.mp3

# Phoebe
uv run python -m holodeck.cli bible add-voice-sample \
  --franchise "Friends" \
  --character "Phoebe Buffay" \
  --sample-file ~/phoebe_sample.mp3

# ... and so on
```

---

## Configuration Options

### Environment Variables

```bash
# 11Labs API Key (required)
ELEVENLABS_API_KEY=sk_xxxxx

# API Rate Limiting
ELEVENLABS_API_RATE_LIMIT=500  # requests/minute (adjust based on plan)

# Voice Synthesis Model
ELEVENLABS_MODEL_ID=eleven_monolingual_v1  # or eleven_multilingual_v2

# Voice Characteristics
ELEVENLABS_VOICE_STABILITY=0.5      # [0.0-1.0] higher = more consistent
ELEVENLABS_SIMILARITY_BOOST=0.75    # [0.0-1.0] higher = more like original

# Optional: Speaker boost (improves audio quality)
ELEVENLABS_USE_SPEAKER_BOOST=false

# Fallback Behavior
ELEVENLABS_FALLBACK_PROVIDER=piper    # Use Piper TTS if 11Labs fails
ELEVENLABS_ENABLE_FALLBACK_LOGGING=true
```

### Database Schema

Voice samples are stored in `actor_voice_samples` table (created by Alembic migration):

```sql
-- Query stored samples
SELECT character_name, elevenlabs_voice_id, upload_date, is_active
FROM actor_voice_samples
WHERE is_active = true;

-- Check for character
SELECT * FROM actor_voice_samples WHERE character_name = 'Rachel Green';
```

---

## Monitoring & Observability

### View 11Labs API Calls

Voice synthesis events are logged via Langfuse (if enabled):

```bash
# Open Langfuse dashboard
open http://localhost:3000
```

**Events tracked**:
- `voice_synthesis_start`: Synthesis attempt initiated
- `voice_synthesis_success`: Audio generated successfully
- `voice_synthesis_failed`: Provider API error (logged with error details)
- `fallback_used`: Fallback to Piper due to 11Labs failure

### Metrics

Check latency and success rate:

```bash
uv run python -m holodeck.observability metrics voice_synthesis \
  --franchise "Friends" \
  --window "24h"
```

---

## Troubleshooting

### Issue: "CharacterNotFoundError" when generating dialogue

**Cause**: No voice sample stored for that character.

**Solution**:
```bash
# Check if sample exists
uv run python -m holodeck.cli bible list-voice-samples --franchise "Friends"

# If missing, add it:
uv run python -m holodeck.cli bible add-voice-sample \
  --franchise "Friends" \
  --character "Rachel Green" \
  --sample-file ~/rachel_sample.mp3
```

### Issue: "Invalid audio file" error during upload

**Cause**: Audio file doesn't meet requirements (format, duration, quality).

**Solution**:
1. Check format: `ffprobe your_file.mp3`
   - Supported: MP3, WAV, OGG, FLAC
2. Check duration: `ffprobe -v error -show_entries format=duration your_file.mp3`
   - Must be 30–600 seconds
3. Check quality: Listen for background noise, clarity
   - 11Labs works best with clean, clear audio

**Convert to MP3** (if needed):
```bash
ffmpeg -i input.wav -codec:a libmp3lame -q:a 2 output.mp3
```

### Issue: "401 Unauthorized" API error

**Cause**: Invalid or missing ELEVENLABS_API_KEY.

**Solution**:
1. Verify API key: `echo $ELEVENLABS_API_KEY`
2. Generate new key at [elevenlabs.io](https://elevenlabs.io) account settings
3. Update `.env` and restart cluster

### Issue: "429 Too Many Requests"

**Cause**: Hit API rate limit (11Labs throttling).

**Solution**:
1. Increase wait time between requests (automatic exponential backoff)
2. Increase `ELEVENLABS_API_RATE_LIMIT` if you have a higher tier
3. Consider spreading productions over time
4. System will automatically fall back to Piper TTS

### Issue: "Silent audio" or "Very quiet dialogue"

**Cause**: Voice characteristics not tuned for actor.

**Solution**:
1. Adjust voice parameters:
   ```bash
   ELEVENLABS_VOICE_STABILITY=0.7  # More consistent delivery
   ELEVENLABS_SIMILARITY_BOOST=0.85  # Closer to original
   ELEVENLABS_USE_SPEAKER_BOOST=true  # Enhance audio quality
   ```
2. Replace voice sample with better quality audio
3. Regenerate production

---

## Testing

### Unit Test Example

```python
# test_elevenlabs_provider.py
import pytest
from holodeck.agents.audio.providers import ElevenLabsVoiceProvider, MockVoiceProvider

@pytest.mark.asyncio
async def test_voice_provider_interface():
    """Any provider can substitute another via protocol."""
    provider = ElevenLabsVoiceProvider(
        api_key="sk_test_xxx",
    )
    
    # Should support any character with stored sample
    audio = await provider.synthesize("Rachel Green", "Hello!")
    assert isinstance(audio, bytes)
    assert len(audio) > 0

@pytest.mark.asyncio
async def test_fallback_on_api_error():
    """Falls back to Piper on API failure."""
    piper_provider = MockVoiceProvider(return_audio=b"fallback_audio")
    elevenlabs_provider = ElevenLabsVoiceProvider(
        api_key="sk_invalid",
    )
    
    fallback = FallbackVoiceProvider(
        primary=elevenlabs_provider,
        fallback=piper_provider,
    )
    
    # Should not raise, returns fallback
    audio = await fallback.synthesize("Rachel Green", "Hello!")
    assert audio == b"fallback_audio"
```

### Integration Test Example

```python
# test_voice_integration.py
@pytest.mark.asyncio
async def test_production_with_voice_cloning():
    """Full E2E test: upload sample → generate dialogue → verify audio."""
    # 1. Add voice sample to Bible
    bible = FranchiseBible("friends")
    bible.add_voice_sample(
        character_name="Rachel Green",
        sample_file="tests/fixtures/rachel_sample.mp3",
    )
    
    # 2. Create Voice Synthesis Agent with 11Labs provider
    voice_agent = VoiceSynthesisAgent(
        provider=ElevenLabsVoiceProvider(api_key=os.getenv("ELEVENLABS_API_KEY")),
    )
    
    # 3. Synthesize dialogue
    context = {
        "script": [
            ("Rachel Green", "That's not even a word!"),
        ],
    }
    result = await voice_agent.process(context)
    
    # 4. Verify output
    assert "audio_files" in result
    assert len(result["audio_files"]) == 1
    assert result["audio_files"][0].endswith(".mp3")
```

---

## Next Steps

After setting up voice cloning for the first character:

1. **Validate Quality**: Listen to generated audio, gather feedback
2. **Add More Characters**: Repeat setup for other cast members
3. **Optimize Settings**: Tune voice_stability and similarity_boost based on quality
4. **Monitor Costs**: Track 11Labs API usage and adjust rate limits if needed
5. **Expand to New Franchises**: Reuse this pattern for other TV shows, movies, etc.

---

## FAQ

**Q: Can I use multiple voice samples per character?**  
A: Currently, only 1 active sample per character is supported. If you want to update, replace the existing sample.

**Q: How much does voice cloning cost?**  
A: 11Labs charges per synthesized character. Expect ~$0.30 per 1000 characters. Pricing varies by plan.

**Q: Can I use voice cloning offline?**  
A: No, 11Labs API requires internet connectivity. Piper TTS (fallback) works offline.

**Q: How long does voice synthesis take?**  
A: Typically 5–10 seconds per 1000 characters (network + API latency). Cached voice IDs are used to skip re-cloning.

**Q: What if the actor's voice changes over time?**  
A: Update the voice sample with a more recent audio clip. System will generate a new voice ID.

**Q: Can I revert to Piper TTS for a character?**  
A: Yes, disable the voice sample: `uv run python -m holodeck.cli bible disable-voice-sample "rachel_green"`
