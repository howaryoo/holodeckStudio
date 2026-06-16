# Research: Media Generation

**Feature**: 002-media-generation
**Date**: 2026-06-09

## MVP Free-Stack Decision

**Constraint**: Laptop with integrated GPU (no discrete GPU, no paid API keys).
**Stack**: $0 per episode, CPU-only inference.

| Modality | MVP Choice | Cost | GPU? | Quality |
|----------|-----------|------|------|---------|
| Dialogue | gTTS (Google TTS) | $0 | No | Robotic but clear |
| Music | _Skipped for MVP_ | $0 | — | Silent soundtrack |
| SFX | _Skipped for MVP_ | $0 | — | No sound effects |
| Video | ImageMagick + FFmpeg | $0 | No | B&W line-art animation |

**Paid upgrades** (bolt-on later, no architecture changes needed):
- Music: Suno API (~$0.03/episode)
- Dialogue: ElevenLabs TTS (~$0.10/episode, better quality)
- SFX: AudioCraft (free but needs GPU)

---

## 1. Dialogue: gTTS (Google Text-to-Speech)

| Factor | Detail |
|--------|--------|
| **Package** | `gtts` (`pip install gtts`) |
| **Input** | Plain text |
| **Output** | .mp3 |
| **Speed** | ~0.5s per line (API call to Google's free endpoint) |
| **Voices** | Multiple languages, single voice per language |
| **Pros** | Free, no API key, instant setup, CPU-only |
| **Cons** | Single voice per language (no multi-character distinction), robotic intonation |
| **Limits** | 100 chars per request soft limit (concatenate for longer) |
| **Docs** | https://pypi.org/project/gTTS/ |

**Voice character workaround**: Prepend character name before each line in the generated audio (e.g. "Eva: We need to move now."), or process per-character with different `lang`/`tld` params for slight variation.

---

## 2. Video: ImageMagick + FFmpeg (B&W line-art)

**Zero API calls at render time.** Deterministic CPU-only pipeline.

### Frame Generation Pipeline
```
Animation text description (from AnimationAgent)
    ↓ Python: parse scene layout, character positions, camera angle
    ↓ ImageMagick: composite SVG primitives → rasterize as PNG
B&W frame sequence
```

SVG templates (pre-defined, not AI-generated):
- Character silhouettes (stick figure / geometric body shapes)
- Environment backdrops (horizon line, walls, doors, windows)
- Prop icons (tables, chairs, consoles, rocks)
- Text overlays (scene title, character name)

Each template is a parameterized SVG string — no LLM involved at render time.

### Video Assembly Pipeline
```
Frame PNG sequence (24fps)
    ↓ FFmpeg concat demuxer
    ↓ Apply B&W color filter (colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0)
    ↓ Multiplex dialogue audio
    ↓ Encode as H.264 .mp4
Final episode video
```

### Why B&W
- 1/3 the bitrate of color
- No color grading pass needed
- Smaller file size, faster encode
- Lower storage costs
- Artistic constraint reinforces silent-film aesthetic

---

## 3. Storage Architecture

All generated media stored in MinIO (already deployed in Phase 1):

```
MinIO bucket: holodeck-media/
└── productions/{production_id}/
    ├── dialogue/
    │   ├── scene-001.mp3
    │   └── scene-002.mp3
    ├── frames/
    │   ├── scene-001-frame-0001.png
    │   └── scene-001-frame-0002.png
    └── final/
        └── episode-101.mp4
```

The `Asset` SQLAlchemy model in postgres.py already supports this:

```python
class Asset(Base):
    __tablename__ = "assets"
    id = Column(UUID, primary_key=True)
    production_id = Column(UUID, ForeignKey("productions.id"))
    episode_id = Column(UUID, ForeignKey("episodes.id"))
    stage = Column(String)        # dialogue, frame, final
    asset_type = Column(String)   # audio/mpeg, image/png, video/mp4
    storage_url = Column(String)  # minio://bucket/key
    metadata_json = Column(JSONB)
```

---

## 4. Dependencies

### Python packages
```toml
[project]
dependencies = [
    "gtts>=2.5.0",          # Google TTS (free, no API key)
    "ffmpeg-python>=0.2.0",  # FFmpeg Python bindings
]
```

### System dependencies (Docker)
```dockerfile
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    fonts-dejavu-core
```

---

## 5. Future Paid Upgrades (no architecture changes needed)

| Upgrade | Replace | Cost | Quality |
|---------|---------|------|---------|
| Music | Add Suno API stage | $0.03/ep | Full soundtrack |
| Better TTS | Swap gTTS → ElevenLabs | $0.10/ep | Multi-voice, emotional |
| SFX | Add AudioCraft stage | $0 (needs GPU) | Environmental audio |
| Color video | Remove B&W filter, add color templates | $0 | More storage/bandwidth |
