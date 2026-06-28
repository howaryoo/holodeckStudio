# Implementation Plan: Sound Effects & Audio Mixing

**Branch**: `008-sound-effects` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)
**Input**: trekcore.com SFX library + existing SoundDesignerAgent text output

## Summary

Add scene-appropriate sound effects (ambience, Foley, SFX) to video output using downloaded trekcore.com MP3 files matched against SoundDesignerAgent text descriptions. FFmpeg mixes dialogue + SFX per scene. Background music deferred (no source yet).

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First | ✅ PASS | FFmpeg subprocess for mixing; Python for matching |
| II. Zen of Python | ✅ PASS | Explicit SFX matching; fallback to dialogue-only on miss |
| III. Single Responsibility | ✅ PASS | SFXMatcher matches; AudioMixer mixes; stage orchestrates |
| IV. Open/Closed | ✅ PASS | New stage added; existing video_assembler unchanged for dialogue-only |
| V. Dependency Inversion | ✅ PASS | SFXMatcher depends on tag index, not concrete files |
| Technology Standards | ✅ PASS | ruff/mypy/pytest |
| Development Workflow | ✅ PASS | Test-first for matcher, mixer |

RESULT: ALL GATES PASS.

## Phases

### Phase 1: SFX Library (4 tasks)
Download + organize trekcore.com sounds. Build tag index.

- T001: Download ~100 Voyager-relevant SFX files from trekcore.com into `sfx_library/`
- T002: Create `src/holodeck/agents/audio/sfx_library.py` — SFXRegistry: tag→file mapping, load index, search by keyword
- T003: Tag index generation script: auto-tag from filename + directory name + manual overrides
- T004: Verify all downloaded files playable (MP3 header check)

### Phase 2: SFX Engine (4 tasks)
Parse SoundDesignerAgent output, match cues to files, mix with dialogue.

- T005: Create `src/holodeck/agents/audio/sfx_matcher.py` — extract SCENE blocks from SoundDesignerAgent output; parse AMBIENCE/FOLEY/SFX lines; keyword → SFXRegistry lookup; return `list[SceneSFXCue]` per scene
- T006: Create `src/holodeck/agents/audio/audio_mixer.py` — FFmpeg amix: dialogue + ambience loops + SFX one-shots per scene; per-stream volume levels; concat scenes into full audio
- T007: Scene-level ambience loop handling — match longest/best ambience track; loop if shorter than scene duration
- T008: Fallback: any scene without matched SFX → dialogue-only (no crash, silent ambience)

### Phase 3: Pipeline Integration (2 tasks)
Wire SFX stage into pipeline. VideoAssembler accepts mixed track.

- T009: Add `sfx_mixer` stage in pipeline after voice_synthesis, before video_assembler; context["sfx_cues"], context["mixed_audio_path"]
- T010: Modify video_assembler to prefer `context["mixed_audio_path"]` when present; fall back to current dialogue-only concat

### Phase 4: Tests (3 tasks)
- T011: Unit tests for SFXRegistry (load index, search by keyword, empty fallback)
- T012: Unit tests for SFXMatcher (parse SoundDesigner output, match cues, no-match fallback)
- T013: Unit tests for AudioMixer (FFmpeg command construction, volume levels, concat chain)
- T014: Integration test — full pipeline with mock SFX library

### Phase 5: Verification (1 task)
- T015: `uv run pytest tests/unit/ -x` — existing 305 + new pass; ruff/mypy clean on new files

## Total: 15 tasks across 5 phases

## Implementation Order
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 (strict sequential)

## Files

| File | Action |
|------|--------|
| `sfx_library/` | NEW — downloaded MP3s + index.json |
| `src/holodeck/agents/audio/sfx_library.py` | NEW — SFXRegistry class |
| `src/holodeck/agents/audio/sfx_matcher.py` | NEW — SFXMatcher class |
| `src/holodeck/agents/audio/audio_mixer.py` | NEW — AudioMixer class |
| `src/holodeck/agents/video/video_assembler.py` | MODIFY — accept mixed_audio_path |
| `src/holodeck/pipeline/runner.py` | MODIFY — add sfx_mixer stage |
| `src/holodeck/pipeline/stages.py` | MODIFY — add SFX_MIXER to enum |
| `tests/unit/test_sfx_library.py` | NEW |
| `tests/unit/test_sfx_matcher.py` | NEW |
| `tests/unit/test_audio_mixer.py` | NEW |

## Deferred
- Background music — no source yet. Future: CC0 music packs or AI music generation.
- ElevenLabs SFX API — optional paid enhancement after basic library matching works.
