# Tasks: Media Generation (Free-Stack MVP)

**Input**: Design documents from `/specs/002-media-generation/`
**Prerequisites**: plan.md (required), research.md (required)
**Dependencies**: Phase 1–9 of 001-holodeck-studio (all 72 tasks)

## Format

- `[ID] [P?] [SYNC/ASYNC] Description`
- **[P]**: Can run in parallel
- **[SYNC]**: Requires human review

---

## Phase 1: Infrastructure & Dependencies

- [ ] T073 [ASYNC] Add system dependencies to Dockerfile: ffmpeg, imagemagick, fonts-dejavu-core
- [x] T074 [ASYNC] Add Python dependencies to pyproject.toml: ffmpeg-python, gtts
- [x] T075 [ASYNC] Create MinIO media helper module in src/holodeck/storage/media_storage.py: upload_media() with content-type from extension, get_media_url(), list_media() using existing ObjectStore protocol; manage holodeck-media bucket lifecycle

---

## Phase 2: Video Generation Agents

- [x] T076 [P] [ASYNC] Create SVG template system in src/holodeck/agents/video/svg_templates.py: reusable SVG component templates (character silhouettes, environment backdrops, prop icons, text overlays) for consistent B&W frame rendering; parameterized Python string templates
- [x] T077 [P] [ASYNC] Implement FrameRendererAgent in src/holodeck/agents/video/frame_renderer.py extending Agent with HolodeckAgentProtocol: read storyboard + animation text → select SVG templates → composite scene frames via ImageMagick → rasterize as B&W PNG → upload to MinIO → return ordered frame URLs
- [x] T078 [P] [ASYNC] Create FFmpeg helper module in src/holodeck/agents/video/ffmpeg_utils.py: async subprocess wrapper for frame concat, audio mixing, B&W filter, video encoding, progress monitoring
- [x] T079 [P] [ASYNC] Implement VideoAssemblerAgent in src/holodeck/agents/video/video_assembler.py extending Agent with HolodeckAgentProtocol: receive frame URLs + dialogue URLs → concat frames at 24fps via FFmpeg → multiplex dialogue onto video → apply B&W filter → encode H.264 .mp4 → upload to MinIO → return final video URL

---

## Phase 3: Dialogue Generation Agent

- [x] T080 [ASYNC] Implement VoiceSynthesisAgent in src/holodeck/agents/audio/voice_synthesis.py extending Agent with HolodeckAgentProtocol: parse script for per-character dialogue lines → call gTTS per line → concatenate per scene → upload .mp3 to MinIO → return dialogue scene URLs

---

## Phase 4: Pipeline Integration

- [x] T081 [SYNC] Wire all media agents into ProductionPipeline runner in src/holodeck/pipeline/runner.py: add VoiceSynthesis + FrameRenderer as parallel stages 20–21 after existing audio stages; add VideoAssembler as stage 22; add PipelineResult fields (dialogue_audio_urls, frame_urls, final_video_url); add CLI display for media URLs; update cache payload
- [x] T082 [ASYNC] Update CLI produce output in src/holodeck/cli/main.py: display media URLs after generation; add `--open` flag to auto-play final video

---

## Phase 5: Testing

- [x] T083 [ASYNC] Create unit tests for svg_templates in tests/unit/test_svg_templates.py: validate SVG output structure, B&W color compliance (<numeric threshold for non-gray pixels), template parameterization
- [x] T084 [ASYNC] Create unit tests for ffmpeg_utils in tests/unit/test_ffmpeg_utils.py: validate frame concat command generation, B&W filter params, audio mix commands
- [x] T085 [ASYNC] Create integration test for media pipeline in tests/integration/test_media_pipeline.py: mock gTTS + ImageMagick + FFmpeg, verify output URLs and MinIO uploads
- [x] T086 [ASYNC] Create end-to-end smoke test script in tests/e2e/test_media_produce.sh: generate a real short test episode (5s realtime), validate .mp4 exists and is playable by ffprobe

---

## Implementation Order

### Phase 1 (Infrastructure)
```
T073 ────┐
T074 ────┤  (parallel)
T075 ────┘
```

### Phase 2 (Video — parallel)
```
T076 ────┐
T077 ────┤
T078 ────┤  (parallel)
T079 ────┘
```

### Phase 3 (Audio)
```
T080 (single task)
```

### Phase 4 (Pipeline wiring — sequential)
```
T081 → T082
```

### Phase 5 (Tests — mostly parallel)
```
T083 ────┐
T084 ────┤
T085 ────┤  (parallel)
T086 ────┘
```

## Total: 14 new tasks

| Phase | Tasks | Count |
|-------|-------|-------|
| Infrastructure | T073–T075 | 3 |
| Video agents | T076–T079 | 4 |
| Dialogue agent | T080 | 1 |
| Pipeline wiring | T081–T082 | 2 |
| Testing | T083–T086 | 4 |
| **Total** | | **14** |
