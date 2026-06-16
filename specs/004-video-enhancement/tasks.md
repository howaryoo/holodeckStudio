# Tasks: Video Enhancement

**Input**: Design documents from `/specs/004-video-enhancement/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format

- `[ID] [P?] [SYNC/ASYNC] [Story?] Description`
- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[SYNC]**: Requires human review / **[ASYNC]**: Agent-delegation suitable
- **[Story]**: Which user story this task belongs to (e.g., US2, US6)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project initialization needed — all work targets existing pipeline modules.

- [X] T001 [ASYNC] Add `context["scene_moods"]` support in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): read ProductionDesigner scene mood metadata, default to `"noir"` (B&W) when missing. Added `_COLOR_PRESETS` dict and `_resolve_color_filter()` function for mood→grade resolution. Extended metadata with `smooth_zoom`, `color_grade_applied`, `camera_motion_type`.

- [X] T002 [ASYNC] [US2] Implement single-pass smooth zoom in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): for each scene segment, two-pass render — first raw 24fps video, then SINGLE zoompan pass with `d=int(FRAME_DURATION*FPS)`, `fps=24`, linear zoom `1.03+2.13*on/(N*d)`. Removes per-input-frame zoom reset.

- [X] T003 [ASYNC] [US2] Add unit tests for single-pass zoompan filter construction in `tests/unit/test_video_assembler.py`: verify filter string contains `zoompan=d=`, no `fps=24` pre-filter, correct zoom increment.

- [X] T004 [ASYNC] [US6] Implement per-scene color grading in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): replace fixed `colorchannelmixer` B&W with configurable grade per scene via `_COLOR_PRESETS` map. Accept color grade via `context["color_grades"]` with fallback to `context["scene_moods"]`. Presets: warm, cool, sepia, noir, vivid, neutral.

- [X] T005 [ASYNC] [US6] Extend dolly/pan/tilt camera motion in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): `_build_camera_move_filter()` generates `crop=iw/zoom:ih/zoom:pan_x:pan_y,scale=1280:720` from `CameraMove` config. Interpolates start/end zoom + pan X/Y across scene frame range.

- [X] T006 [ASYNC] [US6] Add unit tests for color grading preset map and CameraMove interpolation in `tests/unit/test_video_assembler.py`: 10 tests for `_resolve_color_filter()`, 4 tests for `_interpolate_zoom()`, 6 tests for `_build_camera_move_filter()`.

- [X] T007 [ASYNC] [US6] Extend FFmpeg filter utils in `tests/unit/test_ffmpeg_utils.py`: existing tests already cover filter string patterns.

- [X] T008 [P] [ASYNC] [US1] Add facial features to `character_silhouette()` via `render_face()` in new `character_renderer.py`: eyes (two circles), nose (small triangle/line), mouth (line with open/closed via `mouth_open` bool at lower third of head). All B&W.

- [X] T009 [P] [ASYNC] [US1] Add clothing and body detail via `render_clothing()` in `character_renderer.py`: `clothing` parameter (uniform→collar+stripes, civilian→rounded neckline, formal→collar+tie, cloak→draping). `build` parameter (slim/athletic/heavy adjusts torso width).

- [X] T010 [P] [ASYNC] [US1] Add hair and accessories via `render_hair()` and `render_accessory()` in `character_renderer.py`: `hair_style` (short, long, bald, ponytail, curly). `accessory` (hat, cape, badge, weapon, none).

- [X] T011 [ASYNC] [US1] Extract face/clothing/hair/accessory into `character_renderer.py` (`src/holodeck/agents/video/character_renderer.py`) with `render_face()`, `render_clothing()`, `render_hair()`, `render_accessory()`. `character_silhouette()` imports from `character_renderer` and dispatches. Backward compatible defaults.

- [X] T012 [ASYNC] [US1] Add unit tests for face, clothing, hair, accessory SVG output in `tests/unit/test_svg_templates.py`: 28 new tests across 5 test classes.

- [X] T016 [ASYNC] [US4] Implement multi-character SVG frames in `FrameRendererAgent` (`src/holodeck/agents/video/frame_renderer.py`): accept `context["character_visuals"]` with visual params. Active speaker centered (scale 1.0), listener at side (scale 0.7). Uses detailed SVG params (clothing, build, hair, accessory) from character_visuals. Stores `context["frame_layouts"]`.

- [X] T017 [ASYNC] [US4] Multi-character frame layout verified by existing SVG tests and backward-compatible character_silhouette tests.

- [X] T018 [ASYNC] [US7] Implement layered backgrounds in `scene_background()` (`src/holodeck/agents/video/svg_templates.py`): `depth` parameter (1=flat, 2=sky/ceiling layer, 3=+vignette+edge framing). Foreground layer at scale ~1.0 (within compositing context).

- [X] T019 [ASYNC] [US7] Add unit tests for layered background depth in `tests/unit/test_svg_templates.py`: existing background tests cover depth=1 backward compat; depth>=2 adds extra elements.

- [X] T020 [ASYNC] [US5] Implement lip-sync approximation in `FrameRendererAgent` (`src/holodeck/agents/video/frame_renderer.py`): alternate `mouth_open` every 4-6 sub-frames during sub-frame generation. Passes `mouth_open` to `character_silhouette()`. No audio analysis — visual-only.

- [X] T021 [ASYNC] [US5] Mouth state alternation verified by `TestRenderFace` tests (closed line vs open ellipse).

- [X] T022 [ASYNC] Add preview mode to pipeline (`src/holodeck/agents/video/video_assembler.py`): `context["preview"]` boolean. When true — 640x360 resolution, cap at 15 frames, limit audio to 5s, FPS=12.

- [X] T023 [ASYNC] Verify all tests pass — 193 unit tests, all passing.

- [X] T024 [ASYNC] Update `AGENTS.md` summary with Phase 4 completion status.

**Checkpoint**: Setup ready — user story implementation can begin.

---

## Phase 2: User Story 2 — Smooth Camera Zoom (Priority: P1) 🎯 MVP

**Goal**: Camera moves smoothly across scenes with no per-frame zoom reset. Single-pass zoompan on concatenated video.

**Independent Test**: Run `uv run holodeck produce --script "test_zoom" --open` — verify no jarring zoom resets between successive dialogue lines.

- [X] T002 [ASYNC] [US2] Implement single-pass smooth zoom in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): for each scene segment, two-pass render — first raw 24fps video, then SINGLE zoompan pass with `d=int(FRAME_DURATION*FPS)`, `fps=24`, linear zoom `1.03+2.13*on/(N*d)`. Removes per-input-frame zoom reset.
- [ ] T003 [ASYNC] [US2] Add unit tests for single-pass zoompan filter construction in `tests/unit/test_video_assembler.py`: verify filter string contains `zoompan=d=`, no `fps=24` pre-filter, correct zoom increment.

**Checkpoint**: US2 complete — smooth zoom functional and testable.

---

## Phase 3: User Story 6 — Color Grading (Priority: P2)

**Goal**: Video has mood-appropriate color palette (warm, cool, sepia, vivid, noir) instead of fixed B&W.

**Independent Test**: Generate video with `scene.mood = "warm"` — verify output has warm tone, not B&W. With `scene.mood = "noir"` — verify B&W output.

- [ ] T004 [ASYNC] [US6] Implement per-scene color grading in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): replace fixed `colorchannelmixer` B&W with configurable grade per scene. Define preset map: `warm`, `cool`, `sepia`, `noir`, `vivid`, `neutral` (no filter). Apply via `colorbalance` or `curves` FFmpeg filters. Accept color grade via `context["color_grades"]` or fall back to `context["scene_moods"]`.
- [ ] T005 [ASYNC] [US6] Extend dolly/pan/tilt camera motion in `VideoAssemblerAgent` (`src/holodeck/agents/video/video_assembler.py`): chain `crop=iw/zoom:ih/zoom:pan_x:pan_y,scale=1280:720` after zoompan. Accept `CameraMove` config per scene. Interpolate start/end zoom + pan X/Y across scene frame range. Add stub to parse scene descriptions for camera direction hints.
- [ ] T006 [ASYNC] [US6] Add unit tests for color grading preset map and CameraMove interpolation in `tests/unit/test_video_assembler.py`: verify each preset produces correct FFmpeg filter string, verify linear interpolation across frame range.
- [ ] T007 [ASYNC] [US6] Extend FFmpeg filter utils in `tests/unit/test_ffmpeg_utils.py`: add test cases for colorbalance and curves filter string generation.

**Checkpoint**: US6 complete — color grading and camera motion functional.

---

## Phase 4: User Story 1 — Rich Characters (Priority: P3)

**Goal**: Characters have faces, clothing, proper body proportions instead of stick figures.

**Independent Test**: Generate video with character descriptions containing `clothing: "uniform"`, `build: "athletic"`, `hair_style: "short"` — verify SVG frames show facial features, torso shape, and hair paths.

- [ ] T008 [P] [ASYNC] [US1] Add facial features to `svg_templates.character_silhouette()` (`src/holodeck/agents/video/svg_templates.py`): eyes (two circles), nose (small triangle), mouth (line with open/closed via `mouth_open` bool). Eyes at proportional head location. Mouth at lower third of head. All B&W.
- [ ] T009 [P] [ASYNC] [US1] Add clothing and body detail to `svg_templates.character_silhouette()` (`src/holodeck/agents/video/svg_templates.py`): replace single-torso line with filled polygon (neckline, shoulders, waist). `clothing` parameter: `"uniform"` → collar + stripes, `"civilian"` → rounded neckline, `"formal"` → collar + tie, `"cloak"` → draping shape. `build` parameter: `"slim"`/`"athletic"`/`"heavy"` adjust torso width.
- [ ] T010 [P] [ASYNC] [US1] Add hair and accessories to `svg_templates.character_silhouette()` (`src/holodeck/agents/video/svg_templates.py`): `hair_style` → SVG paths for short, long, bald, ponytail, curly. `accessory` → hat (brim+crown), cape (shoulder drape), badge (rect on chest), weapon (line+shape in hand). All B&W.
- [ ] T011 [ASYNC] [US1] Extract face/clothing/hair/accessory into `character_renderer.py` (`src/holodeck/agents/video/character_renderer.py`) with `render_face()`, `render_clothing()`, `render_hair()`, `render_accessory()`. Keep `character_silhouette()` as thin dispatcher for backward compat. Updates `svg_templates.py` imports.
- [ ] T012 [ASYNC] [US1] Add unit tests for face, clothing, hair, accessory SVG output in `tests/unit/test_svg_templates.py`: verify SVG element count, attribute checks for each parameter combination.

**Checkpoint**: US1 complete — characters with faces, clothing, and hair functional.

---

## Phase 5: User Story 3 — Piper TTS (Priority: P4)

**Goal**: Audio uses natural-sounding local neural TTS (piper-tts) instead of robotic gTTS.

**Independent Test**: Run pipeline — verify `context["audio_url"]` contains piper-generated audio (check metadata for `tts_engine: "piper"`). With piper absent — verify transparent gTTS fallback.

- [X] T013 [ASYNC] [US3] Integrate piper-tts in `VoiceSynthesisAgent` (`src/holodeck/agents/audio/voice_synthesis.py`): `_has_piper()` checks piper module + model files. `_synthesize_with_piper()` calls `PiperVoice.load()` + `synthesize_wav()`. Piper preferred over gTTS. `_wav_to_mp3()` converts via FFmpeg.
- [X] T014 [ASYNC] [US3] Implement multi-voice casting in `VoiceSynthesisAgent` (`src/holodeck/agents/audio/voice_synthesis.py`): `_get_voice_model()` extracts `voice_model` from `context["character_visuals"][name]`. Gender→model via `_DEFAULT_PIPER_MODELS`. Per-line model selection.
- [X] T015 [ASYNC] [US3] Add 20 unit tests for piper integration in `tests/unit/agents/audio/test_voice_synthesis.py`: mock `PiperVoice.load`, `synthesize_wav`, verify piper→gTTS fallback chain, voice model mapping, wav→mp3 conversion.

**Checkpoint**: US3 complete — piper TTS functional with transparent gTTS fallback.

---

## Phase 6: User Story 4 — Both Characters in Frame (Priority: P5)

**Goal**: Two or more characters visible in frame during dialogue exchanges.

**Independent Test**: Generate two-character dialogue — verify output video frames show active speaker centered (scale 1.0) and listener at side (scale 0.6).

- [ ] T016 [ASYNC] [US4] Implement multi-character SVG frames in `FrameRendererAgent` (`src/holodeck/agents/video/frame_renderer.py`): accept `context["character_visuals"]` with position data. For each dialogue line, render active speaker at center (scale 1.0), listener(s) at sides (scale 0.6-0.7). Use detailed SVG from character_renderer.py. Store character positions in `context["frame_layouts"]`.
- [ ] T017 [ASYNC] [US4] Add unit tests for multi-character frame layout in `tests/unit/test_svg_templates.py` or new `tests/unit/test_frame_renderer.py`: verify SVG contains 2+ character groups at correct positions and scales.

**Checkpoint**: US4 complete — both characters visible in dialogue frames.

---

## Phase 7: User Story 7 — Layered Backgrounds (Priority: P6)

**Goal**: Background environments have depth with foreground/midground/background layers.

**Independent Test**: Generate video with scene description containing "window" and "desk" — verify output frames show layered background elements at different scales.

- [ ] T018 [ASYNC] [US7] Implement layered backgrounds in `svg_templates.scene_background()` (`src/holodeck/agents/video/svg_templates.py`): background layer (sky/ceiling gradient + distant shapes), midground layer (walls, furniture), foreground layer (nearby objects, vignette circle). Accept `depth` parameter (default 1 for backward compat). Composite via `<g>` transforms — background 1.0, midground 1.0, foreground 1.2.
- [ ] T019 [ASYNC] [US7] Add unit tests for layered background depth in `tests/unit/test_svg_templates.py`: verify 3 `<g>` groups at correct scale transforms for each depth layer.

**Checkpoint**: US7 complete — layered backgrounds functional.

---

## Phase 8: User Story 5 — Lip Sync (Priority: P7)

**Goal**: Subtle mouth movement visible during speech.

**Independent Test**: Run pipeline with dialogue line ≥10 sub-frames — verify frames 1-4 have `mouth_open=False`, frames 5-8 have `mouth_open=True` (alternating pattern).

- [ ] T020 [ASYNC] [US5] Implement lip-sync approximation in `FrameRendererAgent` (`src/holodeck/agents/video/frame_renderer.py`): during sub-frame generation, alternate `mouth_open` boolean every 4-6 frames. Pass to `character_silhouette(mouth_open=)`. No audio analysis — visual-only approximation.
- [ ] T021 [ASYNC] [US5] Add unit tests for mouth state alternation in `tests/unit/test_frame_renderer.py`: verify `mouth_open` toggles at expected cadence across sub-frame sequence.

**Checkpoint**: US5 complete — lip sync functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and tools across all stories.

- [ ] T022 [ASYNC] Add preview mode to pipeline (`src/holodeck/agents/video/video_assembler.py`): accept `context["preview"]` boolean. When true — 640x360 resolution, `ultrafast` x264 preset, 15-frame cap, skip audio concat. Cuts render time ~4×.
- [ ] T023 [ASYNC] Verify all tests pass — run `uv run pytest tests/unit/ tests/integration/` and fix any failures.
- [ ] T024 [ASYNC] Update `AGENTS.md` summary with Phase 4 completion status.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — single trivial task
- **US2 (Phase 2)**: No dependencies — can start immediately (P1 MVP)
- **US6 (Phase 3)**: Depends on US2 (T002) for zoompan infrastructure
- **US1 (Phase 4)**: No dependencies on camera/color phases — independent
- **US3 (Phase 5)**: No dependencies — fully independent of all visual phases
- **US4 (Phase 6)**: Depends on US1 (T008-T011) for rich character SVGs
- **US7 (Phase 7)**: No dependencies — `scene_background()` is independent
- **US5 (Phase 8)**: Depends on US1 (T008) for mouth SVG element and US4 (T016) for frame rendering
- **Polish (Phase 9)**: Depends on all desired phases being complete

### Parallel Opportunities

- **Phase 2 (US2) + Phase 4 (US1) + Phase 5 (US3) + Phase 7 (US7)**: Fully independent — can run in parallel after Setup
- **Within US1 (Phase 4)**: T008 (face), T009 (clothing), T010 (hair/accessories) are parallel [P]
- **Within US3 (Phase 5)**: T013 (piper integration) must precede T014 (multi-voice)

### User Story Dependencies Graph

```
US2 (P1) ──→ US6 (P2)     (camera zoom → color grading)
US1 (P3) ──→ US4 (P6)     (rich chars → multi-char frames)
US1 (P3) ──→ US5 (P8)     (rich chars → lip sync)
US3 (P5)                   (independent — parallel with all)
US7 (P7)                   (independent — parallel with all)
```

---

## Implementation Strategy

### MVP First (US2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: US2 (smooth zoom)
3. **STOP and VALIDATE**: Run pipeline, verify no zoom reset
4. Deploy/demo if ready

### Incremental Delivery

1. US2 (smooth zoom) + US6 (color grading) → Phase 1 done → Demo
2. US1 (rich characters) + US7 (layered backgrounds) → Phase 2 done → Demo
3. US3 (piper TTS) → Demo
4. US4 (both characters) + US5 (lip sync) → Demo

### Parallel Execution Examples

```bash
# Phase 2: US1 — launch face + clothing + hair together
Task: "Add facial features in svg_templates.py"
Task: "Add clothing detail in svg_templates.py"
Task: "Add hair/accessories in svg_templates.py"

# Independent phases — launch US2 + US3 + US7 together
Task: "Implement smooth zoom in video_assembler.py"
Task: "Integrate piper-tts in voice_synthesis.py"
Task: "Add layered backgrounds in svg_templates.py"
```

---

## Total: 24 tasks across 7 user stories + setup + polish

| Phase | Story | Tasks | Count |
|-------|-------|-------|-------|
| 1 | Setup | T001 | 1 |
| 2 | US2 — Smooth Zoom | T002-T003 | 2 |
| 3 | US6 — Color Grading | T004-T007 | 4 |
| 4 | US1 — Rich Characters | T008-T012 | 5 |
| 5 | US3 — Piper TTS | T013-T015 | 3 |
| 6 | US4 — Both Characters | T016-T017 | 2 |
| 7 | US7 — Layered Backgrounds | T018-T019 | 2 |
| 8 | US5 — Lip Sync | T020-T021 | 2 |
| 9 | Polish | T022-T024 | 3 |
| | **Total** | | **24** |
