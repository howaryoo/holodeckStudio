# Feature Specification: Video Quality Improvements

**Feature Branch**: `003-video-quality`
**Created**: 2026-06-10
**Status**: Draft
**Input**: User feedback — video is watchable but static, stick-figure quality, hard cuts between scenes, voices sound identical per character

**Goal**: Improve generated video watchability using free-stack tools (FFmpeg, SVG manipulation) without GPU or paid APIs.

**Success Criteria**:
- Scene transitions use crossfade instead of hard cut
- Subtitles appear at bottom of frame matching dialogue timing
- Each character has distinct voice pitch (even with gTTS)
- Environment backgrounds include furniture/objects from story context
- Simple character animation (breathing, head movement, arm gestures)
- Characters are visually distinct (height, silhouette details)

**Non-Goals**:
- No GPU-accelerated rendering (no CUDA, no AI image gen)
- No paid TTS or voice cloning
- No 3D animation or skeletal rigging
- No lip sync

**Constraints**:
- $0 cost total (no API keys, no cloud services beyond optional MinIO)
- Must use FFmpeg, ImageMagick, gTTS, Python SVG string manipulation only
- Must integrate into existing 22-stage pipeline
- Must maintain backward compatibility (cache schema, PipelineResult, CLI)

## Clarifications

- Q: How should crossfades work with per-dialogue-line frames? → A: Group frames by scene, apply xfade between scene groups, not between every frame. Each scene becomes a segment.
- Q: Should subtitles be burned in or soft? → A: Burned in via FFmpeg drawtext. Soft subtitles (separate SRT) would require player support.
- Q: How to measure "character distinctness"? → A: Height ratio ≥1.1 between tallest and shortest character; unique silhouette elements per character (hat, cape, hairstyle, weapon).

## User Scenarios

1. User generates video → sees smooth crossfades between scene changes instead of hard cuts
2. User reads subtitles at bottom of frame during playback (helpful for accessibility)
3. User hears different voice pitch for Captain Voss vs Ambassador Zyn
4. User sees recognizable furniture (desk, console, table) matching story setting
5. User sees character breathe (subtle head/torso movement) during dialogue
6. User can distinguish characters by silhouette alone (hat, cape, height)
