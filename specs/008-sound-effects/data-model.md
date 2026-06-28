# Data Model: Sound Effects

## New Context Keys

| Key | Type | Description | Set By |
|-----|------|-------------|--------|
| `sfx_enabled` | `bool` | Enable/disable SFX mixing. Default True. Set False by `--no-sfx` CLI flag. | Pipeline init |
| `sound_design` | `str` | SoundDesignerAgent output text (existing key, now consumed by SFX stage) | SoundDesignerAgent |
| `dialogue_audio_urls` | `dict[int, str]` | Per-scene dialogue file paths (existing key, now consumed by SFX stage) | VoiceSynthesisAgent |
| `mixed_audio_path` | `str` | Path to final mixed audio file (dialogue + ambience + SFX). Written by sfx_mixer stage, read by VideoAssemblerAgent. | AudioMixer (via sfx_mixer stage) |
| `scene_durations` | `list[float]` | Duration in seconds per scene. Used by AudioMixer for ambience looping. | Pipeline (from script timing) |

## New Data Structures

### SFXEntry (sfx_library.py)
```
@dataclass
class SFXEntry:
    path: str          # relative path from sfx_library/
    category: str      # directory name (background, computer, doors, etc.)
    filename: str      # base name without extension
    tags: list[str]    # search keywords
    duration: float    # seconds (from ffprobe)
    is_loopable: bool  # suitable for seamless loop (ambience)
```

### SceneCue (sfx_matcher.py)
```
@dataclass
class SceneCue:
    scene_number: int
    location: str         # from "SCENE N: Location"
    ambience: str         # raw ambience description
    foley: str            # raw foley description
    sfx: list[str]        # individual SFX descriptions split on commas

@dataclass
class MatchedScene:
    scene_number: int
    location: str
    ambience_path: str | None   # matched ambience file or None
    foley_paths: list[str]       # matched foley files
    sfx_paths: list[str]         # matched SFX files
```

## SFX Library Structure

```
sfx_library/
├── index.json                  # auto-generated search index
├── tag_overrides.yaml          # manual tag adjustments
├── background/                 # ambient background loops
│   ├── voy_bridge.mp3
│   ├── voy_engineering.mp3
│   └── ...
├── aliensounds/                # alien/Borg specific
│   ├── borg_adapt_1.mp3
│   └── ...
├── computer/                   # beeps, alerts, alarms
├── doors/
├── medical/
├── redalert/
├── transporter/
├── weapons/
└── ...
```

## Audio Levels

| Stream | Gain | dB | Notes |
|--------|------|----|-------|
| Dialogue | 1.0 | 0dB | Reference level |
| Ambience | 0.25 | -12dB | Looped, faded under dialogue |
| Foley | 0.5 | -6dB | One-shot at action point |
| SFX | 0.5 | -6dB | One-shot at action point |

## Pipeline Stage

```
Stage order:
  COMPOSER → SOUND_DESIGNER → VOICE_DIRECTOR → VOICE_SYNTHESIS
  → SFX_MIXER (NEW) → FRAME_RENDERER → VIDEO_ASSEMBLER
```

SFX_MIXER inserted between VOICE_SYNTHESIS and FRAME_RENDERER:
- Input: sound_design (text), dialogue_audio_urls (per-scene dialogue paths)
- Output: mixed_audio_path (full mixed audio track)
- Skip: if sfx_enabled=False or library empty or FFmpeg missing
