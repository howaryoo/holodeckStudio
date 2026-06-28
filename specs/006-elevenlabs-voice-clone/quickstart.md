# Quickstart: 11Labs Voice Clone Integration

**Date**: 2026-06-25
**Audience**: Developers and admins setting up voice cloning for a new franchise or character

---

## 5-Minute Setup

### 1. Add API Key

```bash
# .env
ELEVENLABS_API_KEY=sk_your_key_here
```

### 2. Run the Database Migration

```bash
make start                        # cluster + port-forwards
uv run alembic upgrade head       # applies migration 003 (actor_voice_samples table)
```

### 3. Upload a Voice Sample

```bash
uv run holodeck bible voice-sample add \
  --bible <bible-id> \
  --character "Rachel Green" \
  --file ~/rachel_sample.mp3
```

### 4. Produce with Voice Cloning

```bash
uv run holodeck produce "Rachel visits Central Perk..." \
  --bible <bible-id>
# ElevenLabs provider activates automatically for characters with stored samples
```

---

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.11+ | via `uv` |
| `ffprobe` | any | already a system dep (installed with `ffmpeg`) |
| `elevenlabs` SDK | ≥1.0.0 | already in `pyproject.toml` |
| MinIO | running | via `make start` |
| PostgreSQL | running | via `make start` |

---

## Voice Sample Requirements

- **Duration**: 15–600 seconds (15s minimum for acceptable clone quality)
- **Formats**: MP3, WAV, OGG, FLAC
- **Quality**: Clear audio, minimal background noise, mono or stereo
- **Content**: Ideally dialogue-only (no music, minimal ambience)

**Tip**: A 45–60 second clip of clear TV dialogue gives the best clone quality on the free tier.

**Convert WAV to MP3** (if needed):
```bash
ffmpeg -i input.wav -codec:a libmp3lame -q:a 2 output.mp3
```

**Check audio duration**:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 your_file.mp3
```

---

## Configuration Reference

All settings live in `.env`:

```bash
# Required
ELEVENLABS_API_KEY=sk_xxxxx

# Voice quality tuning (optional — these are the defaults)
ELEVENLABS_VOICE_MODEL=eleven_monolingual_v1
ELEVENLABS_VOICE_STABILITY=0.5          # [0.0–1.0] higher = more consistent, less variation
ELEVENLABS_SIMILARITY_BOOST=0.75        # [0.0–1.0] higher = closer to original voice
ELEVENLABS_USE_SPEAKER_BOOST=false      # true = better quality, uses more credits
```

**Free tier budget**: ~10,000 characters/month. One 5-minute Friends scene ≈ 3,000 chars.

---

## CLI Reference

```bash
# Add a voice sample to a bible
uv run holodeck bible voice-sample add \
  --bible <bible-id> \
  --character "Rachel Green" \
  --file ~/sample.mp3 \
  [--description "S01E01 coffee shop scene"]

# List all voice samples for a bible
uv run holodeck bible voice-sample list --bible <bible-id>

# Disable a voice sample (falls back to Piper TTS)
uv run holodeck bible voice-sample disable --bible <bible-id> --character "Rachel Green"
```

---

## How Voice Selection Works

At runtime, `VoiceSynthesisAgent.process()` checks each character in the script:

```
For each dialogue line (char_name, text):
    1. Query ActorVoiceSample for (bible_id, char_name, is_active=True)
    2. If found AND ELEVENLABS_API_KEY set:
         → ElevenLabsProvider.synthesize()
         → On API error: log warning, fall back to PiperProvider
    3. If not found OR no API key:
         → PiperProvider.synthesize() (existing Piper logic, unchanged)
```

---

## Troubleshooting

### "Audio validation failed: duration out of range"

Duration must be 15–600 seconds. Check with:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 your_file.mp3
```

### "401 Unauthorized" from ElevenLabs

API key is missing or wrong. Verify:
```bash
grep ELEVENLABS_API_KEY .env
```

### "429 Too Many Requests"

Free tier rate limited. System falls back to Piper TTS automatically (logged as warning).
Wait and retry, or spread productions over time.

### Voice sounds robotic / low quality

- Increase `ELEVENLABS_VOICE_STABILITY=0.7` (more consistent)
- Increase `ELEVENLABS_SIMILARITY_BOOST=0.85` (closer to original)
- Try `ELEVENLABS_USE_SPEAKER_BOOST=true` (uses more credits)
- Use a higher quality audio sample (cleaner audio, less background noise)

### Production completes but voice is Piper (not cloned)

Check that:
1. `ELEVENLABS_API_KEY` is set in `.env`
2. A voice sample exists: `uv run holodeck bible voice-sample list --bible <id>`
3. Character name in the sample exactly matches the script character name (case-insensitive)
