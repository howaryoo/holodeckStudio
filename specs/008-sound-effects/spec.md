# Feature Specification: Sound Effects & Audio Mixing

**Feature Branch**: `008-sound-effects`
**Created**: 2026-06-28
**Status**: Planning complete → Implementation ready

**Input**: Pipeline has `SoundDesignerAgent` that produces text descriptions of sound effects, and `ComposerAgent` that produces text musical scores. Dialogue audio exists (ElevenLabs/Piper). No ambience, Foley, or SFX audio in output — silence between dialogue.

**Change**: Replace silence with scene-appropriate sound effects by matching SoundDesignerAgent text cues against downloaded TrekCore.com SFX library. Mix via FFmpeg. Background music deferred.

## Success Criteria

- Each scene has ambient background audio (bridge hum, sickbay beeps, etc.)
- Character actions produce Foley (door hiss, hypospray, transporter)
- Sound effects degrade to dialogue-only if library is empty or matching fails
- Audio levels: dialogue ≈ 0dB, ambience ≈ -12dB, SFX ≈ -6dB
- `--no-sfx` flag produces original dialogue-only output (no regression)

## Non-Goals

- No background music (deferred — needs library source or AI music generation)
- No AI SFX generation (ElevenLabs SFX API deferred)
- No procedural audio
- No real-time mixing

## SFX Source

**TrekCore.com** (`https://www.trekcore.com/audio/`) — fan site hosting Star Trek sound clips. Direct MP3 downloads organized by category. ~100 files downloaded locally into `sfx_library/`. Experimental/personal use.

## Architecture

```
SoundDesignerAgent (text) ──→ SFXMatcher ──→ SFX paths per scene
                                                  ↓
VoiceSynthesisAgent (dialogue MP3s) ──→ AudioMixer (FFmpeg amix)
                                             ↓
                                        Mixed audio track
                                             ↓
VideoAssemblerAgent (video + mixed audio)
```

## Files

| File | Description |
|------|-------------|
| `sfx_library/` | Downloaded MP3s + index.json |
| `src/holodeck/agents/audio/sfx_library.py` | SFXRegistry: tag-indexed file search |
| `src/holodeck/agents/audio/sfx_matcher.py` | Parse SoundDesigner output → match cues |
| `src/holodeck/agents/audio/audio_mixer.py` | FFmpeg amix layering |
| `src/holodeck/pipeline/runner.py` | +SFX_MIXER stage |
| `src/holodeck/agents/video/video_assembler.py` | Accept mixed_audio_path |

## Dependencies

- FFmpeg (existing system dep)
- Python stdlib only for new code (os, re, json, subprocess, dataclasses)

## License Note

TrekCore.com sounds derived from Star Trek TV series/films — owned by CBS/Paramount. User assumes responsibility for experimental/personal use only.
