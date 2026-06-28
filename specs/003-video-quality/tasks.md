# Tasks: Video Quality Improvements

**Input**: Design documents from `/specs/003-video-quality/`
**Prerequisites**: plan.md (required), research.md (required), spec.md (required)
**Dependencies**: Phase 10 of 002-media-generation (all 14 tasks) — video pipeline must be functional

## Format

- `[ID] [P?] [SYNC/ASYNC] [R?] Description`
- **[P]**: Can run in parallel
- **[SYNC]**: Requires human review
- **[ASYNC]**: Agent-delegation suitable
- **[R]**: Risk level (Low/Medium/High)

---

## Phase 1: Audio & Subtitles

- [ ] T087 [ASYNC] [Low] Implement per-character audio pitch shift in `src/holodeck/agents/video/ffmpeg_utils.py`: add `build_pitch_shift_cmd(audio_path: str, semitones: float, output_path: str)` function using FFmpeg `asetrate` + `aresample`. Map character names to pitch semitones (male → -2, female → +3, neutral → 0). Test with 3 pitch variants.
  - **Classification Justification**: Standard library/FFmpeg pattern, well-defined I/O, testable units
  - **Rationale**: FFmpeg filter chain is deterministic; no LLM or complex business logic

- [ ] T088 [ASYNC] [Low] Add subtitle timing data to `FrameRendererAgent.process()` output metadata in `src/holodeck/agents/video/frame_renderer.py`: for each dialogue line frame, include `{"dialogue_text": "...", "character": "..."}` in a list. Store as `context["subtitle_data"]` for VideoAssembler consumption.
  - **Classification Justification**: Boilerplate data plumbing, clear schema
  - **Rationale**: Append-only metadata field; no existing code modified

- [ ] T089 [ASYNC] [Low] Add subtitle burning to `VideoAssemblerAgent` in `src/holodeck/agents/video/video_assembler.py`: after audio concat step, apply `drawtext` filter with each dialogue line's text, positioned at bottom-center, white text on semi-transparent black background, synced to frame timing. Use subtitle_data from context.
  - **Classification Justification**: FFmpeg drawtext is a standard filter; deterministic output
  - **Rationale**: Same pattern as existing zoompan/B&W filters in video_assembler

---

## Phase 2: Scene Transitions

- [ ] T090 [ASYNC] [Medium] Modify `VideoAssemblerAgent` to split video into per-scene segments before assembly: group frames by scene (from subtitle_data or frame metadata), generate separate .mp4 per scene group, store in tempdir.
  - **Classification Justification**: Well-defined algorithm with clear edge cases
  - **Rationale**: Scene grouping logic is pure data manipulation; video generation reuses existing ImageMagick+FFmpeg path

- [ ] T091 [ASYNC] [Medium] Implement crossfade concatenation in `VideoAssemblerAgent`: after per-scene segments are generated, use FFmpeg `xfade` filter chain to join segments with `fadeblack` transition (1s duration). Handle N scenes with cascaded filter graph. Fall back to concat if xfade not available.
  - **Classification Justification**: FFmpeg xfade chain is documented algorithm; no state machine/LLM
  - **Rationale**: Cascaded xfade is a known FFmpeg pattern; fallback is simple conditional

---

## Phase 3: Richer Visuals

- [ ] T092 [ASYNC] [Low] Extend `svg_templates.scene_background()` in `src/holodeck/agents/video/svg_templates.py`: accept optional `props` parameter (list of furnishing keywords). When location includes keywords like "desk", "console", "table", "window", "door", render additional SVG elements using `prop_icon()` or new shapes. Keep B&W compliance.
  - **Classification Justification**: Pure SVG string manipulation; no side effects
  - **Rationale**: Extends existing templates with additional conditionals; existing B&W tests validate

- [ ] T093 [ASYNC] [Low] Improve `svg_templates.character_silhouette()` in `src/holodeck/agents/video/svg_templates.py`: add optional parameters for hair, clothing, accessory, and height_ratio. Each adds B&W SVG elements. All parameters default to current behavior when omitted.
  - **Classification Justification**: Pure SVG string manipulation with backward-compatible defaults
  - **Rationale**: Optional params = zero risk to existing callers; all existing tests still pass

- [ ] T094 [ASYNC] [Medium] Add per-character animation frames to `FrameRendererAgent` in `src/holodeck/agents/video/frame_renderer.py`: for each dialogue line, generate N sub-frames (N=3-5) with small pose deltas (head bob y±2px, arm angle delta ±5°, torso sway). Label sub-frames as `---NEXT FRAME---` in output so VideoAssembler treats them as separate frames.
  - **Classification Justification**: Deterministic SVG delta generation; no external calls
  - **Rationale**: Math-only coordinate manipulation; same pattern as existing silhouette generator

- [ ] T095 [ASYNC] [Low] Handle increased frame count from T094 in `VideoAssemblerAgent`: when animation sub-frames exist, use shorter FRAME_DURATION per sub-frame (total per-dialogue-line time ÷ N sub-frames). Maintain audio sync — one audio file still spans its dialogue line, multiple sub-frames play during that window.
  - **Classification Justification**: Simple division logic; modifies existing FRAME_DURATION calculation
  - **Rationale**: Minute change to duration math in video_assembler; audio concat unaffected

---

## Implementation Order

### Phase 1 (parallel)
```
T087 ────┐
T088 ────┤
T089 ────┘
```

### Phase 2 (sequential)
```
T090 → T091
```
(Dependency: Phase 1 for subtitle timing data)

### Phase 3 (parallel)
```
T092 ────┐
T093 ────┤  (all modify svg_templates or frame_renderer)
T094 ────┤
T095 ────┘
```

## Total: 9 tasks

| Phase | Tasks | Count |
|-------|-------|-------|
| Audio & Subtitles | T087–T089 | 3 |
| Scene Transitions | T090–T091 | 2 |
| Richer Visuals | T092–T095 | 4 |
| **Total** | | **9** |
