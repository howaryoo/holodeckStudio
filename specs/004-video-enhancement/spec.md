# Feature Specification: Video Enhancement

**Feature Branch**: `004-video-enhancement`
**Created**: 2026-06-11
**Status**: Draft
**Input**: User feedback — video is still poor quality after 003-video-quality (static stick figures, no smooth camera, robotic gTTS, B&W only, no simultaneous character framing)

**Goal**: Transform output from "barely watchable technical demo" to "actually watchable short film" using free-stack tools only. No GPU, no paid APIs.

**Success Criteria**:
- Characters have faces, clothing, proper body proportions (not stick figures)
- Camera moves smoothly across scenes (no per-frame zoom reset)
- Two characters visible in frame during dialogue exchanges (active speaker + one listener)
- Background environments have depth (foreground/midground/background layers)
- Audio uses natural-sounding local neural TTS (piper-tts) instead of gTTS
- Video has color grading or mood-appropriate palette (not pure B&W)
- Subtle lip movement visible during speech (mouth shape on/off)
- Scene-level animation: dolly, pan, tilt camera moves

**Non-Goals**:
- No GPU-accelerated rendering (no CUDA, no AI image gen)
- No paid TTS, voice cloning, or cloud APIs
- No 3D models or skeletal animation
- No machine learning or AI upscaling
- No real-time playback or streaming
- No audio ducking or multi-track mixing

**Constraints**:
- $0 cost total
- Must use FFmpeg, ImageMagick, Python SVG manipulation only
- Must integrate into existing pipeline (stages 20-22 remain)
- Must maintain backward compatibility (cache, PipelineResult, CLI unchanged)
- piper-tts is the only new dependency (local, free, CPU-only)

## Clarifications

- Q: How to handle multi-character frames? → A: FrameRendererAgent generates layout SVG for each line: active speaker centered+large, listener(s) at sides smaller. Not full split-screen — more like over-the-shoulder or two-shot.
- Q: What about character design consistency across frames? → A: CharacterDesigner agent already generates character descriptions. Use these to drive SVG template parameters (hair style, clothing, height) deterministically.
- Q: How to achieve smooth camera motion? → A: Render all frames as a single video segment, apply zoompan ONCE to the concatenated video. Per-frame zoom resets eliminated.
- Q: Color palette approach? → A: Replace `colorchannelmixer` B&W with `curves` or `colorbalance` filters to apply sepia, cool-tone, or warm-tone grading per scene mood.
- Q: How is scene mood determined? → A: Stage 9 (ProductionDesigner) already emits `scene.mood` metadata per scene. Use `context.get("scene_moods", {})` keyed by scene ID. Default to `"noir"` (B&W) when missing. No separate mood-detection model needed.
- Q: How do character visual params reach the rendering pipeline? → A: Extract from existing CharacterDesigner `AgentOutput.metadata` via `context["character_visuals"]` dict. No new agents or CLI flags.
- Q: Max characters per multi-character frame? → A: 2 max — active speaker (center) + one listener (side). Prevents clutter.
- Q: Error handling policy for Phase 4 features? → A: Graceful degradation with warning — each feature fails independently. Piper→gTTS fallback, B&W when grading fails, single-character when multi-char frame errors. No hard abort.

## User Scenarios

1. User generates video → sees characters with faces, hair, clothing (not stick figures)
2. User sees smooth camera zoom across entire scene instead of per-frame jump
3. User hears natural-sounding dialogue from piper-tts (not robotic gTTS)
4. User sees both characters during conversation, not just the active speaker
5. User sees subtle mouth movement when characters speak
6. User sees color-graded video matching story mood (warm sunset, cold spaceship, etc.)
7. User sees layered backgrounds with depth (foreground objects, midground action, background scenery)
