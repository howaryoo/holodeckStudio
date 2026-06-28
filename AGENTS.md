# Holodeck Studio — Session Summary

<!-- SPECKIT START -->
**Active Plan**: `specs/008-sound-effects/plan.md` (Sound Effects — all 15 tasks complete)
**Previous Plan**: `specs/007-ai-video-generation/plan.md` (AI Video Generation — all 19 tasks complete)
<!-- SPECKIT END -->

## Goal
All 86 baseline tasks + 27 video enhancement + 15 sound effects = 128 tasks complete.

## Constraints
- `uv` only for package management
- Model providers abstracted via Agno; configurable via env vars
- All agents: `@observe`, optional `model` kwarg, `process()` + `review_output()`
- Spec-driven: spec kit (spec.md → plan.md → research.md → tasks.md → impl)
- Media: $0, no GPU, no paid APIs — piper-tts/gTTS, ImageMagick, FFmpeg
- System deps: `ffmpeg`, `convert` (ImageMagick), `piper-tts` (Python package v1.4.2, ONNX CPU)

## Progress

### Phase 4 Video Enhancement — 27 tasks complete
- **T001**: Scene mood support via `context["scene_moods"]` in VideoAssemblerAgent
- **T002-T003**: Single-pass smooth zoom (two-pass render: raw 24fps → zoompan ONCE, linear 1.03→3.16)
- **T004-T007**: Per-scene color grading presets (warm/cool/sepia/noir/vivid/neutral) + dolly/pan/tilt camera moves
- **T008-T012**: Rich character SVGs — faces (eyes/nose/mouth), clothing (4 types), hair (5 styles), accessories (4 types) extracted into `character_renderer.py`
- **T013-T015**: Piper TTS integration — `_has_piper()`, `_synthesize_with_piper()`, `_wav_to_mp3()`, multi-voice casting via `character_visuals["voice_model"]`, gTTS fallback. 20 unit tests. Models: `en_US-lessac-medium` (female, 60MB), `en_US-libritts_r-medium` (male, 75MB) in `piper_models/`
- **T016-T017**: Multi-character frames (active speaker center + listener at side, 2 max)
- **T018-T019**: Layered backgrounds (depth=1: flat, depth=2: +sky/ceiling, depth=3: +vignette/framing)
- **T020-T021**: Lip-sync approximation (mouth open/closed toggle every 4-6 sub-frames)
- **T022**: Preview mode (640x360, 15-frame cap, FPS=12)
- **T023-T024**: 231 tests passing (220 unit + 11 integration), AGENTS.md updated

### Phase 5 Sound Effects — 15 tasks complete
- **T001**: 130+ SFX MP3s downloaded from trekcore.com into `sfx_library/{category}/`
- **T002-T003**: `SFXRegistry` + `build_sfx_index.py` — tag-indexed library search, 130 entries in `index.json`
- **T004**: All files verified playable and searchable
- **T005**: `SFXMatcher` — regex-parses SoundDesignerAgent SCENE blocks, matches cues to SFX files
- **T006-T007**: `AudioMixer` — FFmpeg `amix` per-scene layering (dialogue 0dB, ambience -12dB, SFX -6dB), `aloop`/`atrim` for ambience, `concat` for scene assembly
- **T008**: Graceful fallback on any failure (empty library, partial match, missing FFmpeg → dialogue-only)
- **T009**: `SFX_MIXER` stage inserted in runner.py between voice_synthesis and frame_renderer
- **T010**: VideoAssembler uses `context["mixed_audio_path"]` when present
- **T011-T013**: 22 unit tests (8+7+7) — all pass
- **T014**: 7 integration tests — pipeline mock, mix, concat, fallback
- **T015**: `ruff check` 0 errors on source, `mypy` 0 errors on source, all 29 SFX tests + full 327-unit suite pass

### Done (86 baseline tasks)
- **Phases 1-10**: All T001-T086 complete (pipeline, agents, media gen, cache, etc.)

## Known Issues
- Zoompan with image2 input: `on` resets per input frame in single-pass mode, but two-pass (raw video → zoompan) approach works correctly
- Preview mode skips audio concat — audio-free raw video only
- `character_visuals` context key consumed by FrameRendererAgent but not auto-populated — CharacterDesigner must supply it
- `face_shape` data model field defined but not consumed by `render_face()` (deferred)
- `CameraMove` population: no task parses scene descriptions for camera direction hints (stub only)
- **Replicate API key is invalid (401 Unauthenticated)** — `r8_IYluyFz...` key in `.env` returns 401. AI video generation silently falls back to SVG. Need valid key from https://replicate.com.
- **ReplicateProvider auth fixed**: `replicate v1.0.7` caches API token at import time via `Client()` singleton. Setting `REPLICATE_API_TOKEN` env var after import has no effect. Fixed by creating a fresh `Client(api_token=key)` per call instead of using the module-level `replicate.run()`.
- **SFX mixer dead code (FIXED)**: `dialogue_audio_urls` was `list[str]` (from VoiceSynthesisAgent) but mixer expected `dict[str,str]`. Dialogue-by-scene lookup always failed → zero scenes mixed → no SFX output. Fixed by concatting all dialogue files, dividing evenly across matched scenes.

## Key Decisions
- **Two-pass zoom**: Raw 24fps video first, then zoompan ONCE on the video stream. Avoids FFmpeg zoompan `on` reset with image2 input.
- **Color grading fallback**: `context["color_grades"]` > `context["scene_moods"]` > default `"noir"` (B&W). Each scene independently configurable.
- **Rich character defaults**: All new params (`mouth_open`, `clothing`, `build`, `hair_style`, `accessory`) default to backward-compatible values. `character_silhouette()` signature unchanged for existing callers.
- **character_renderer.py**: Extracted from `svg_templates.py` to satisfy SR (Principle III). `character_silhouette()` imports and dispatches to `render_face/clothing/hair/accessory`.
- **Max 2 characters per frame**: Active speaker center + one listener at side. Prevents clutter.
- **Lip sync visual-only**: No audio waveform analysis — frame-counter-based toggle every 4-6 sub-frames.
- **Piper TTS**: Python package `piper-tts==1.4.2` via `uv add`. Models downloaded to `piper_models/` from HuggingFace. `_has_piper()` checks spec + model files. `_synthesize_with_piper()` uses `PiperVoice.load()` + `synthesize_wav()`. WAV→MP3 via FFmpeg. Gender→model mapping via `_DEFAULT_PIPER_MODELS`. Per-character voice via `context["character_visuals"][name]["voice_model"]`.
- **Graceful degradation**: All Phase 4 features degrade independently — B&W when grading fails, single-char when multi-char errors, gTTS when piper absent.
- **SFX download naming**: Used actual href values from trekcore.com HTML page (e.g., `alarm01.mp3` not `alarm_1.mp3`) — initial batch had 45 failures from assumed names, corrected to actual filenames
- **Path resolution**: SFXEntry.path stores relative path from `sfx_library/`; SFXMatcher resolves to absolute path via `registry.library_path.resolve()`; AudioMixer checks `os.path.exists` before using
- **FFmpeg filter labels**: Outputs tracked via `out_labels` list (e.g. `[d]`, `[a]`, `[s0]`) not parsed from filter strings
- **Stream index**: Tracked incrementally with `stream_idx` counter, not computed from `len(inputs)//2`
- **Two-pass zoom**: Raw 24fps video first, then zoompan ONCE on the video stream. Avoids FFmpeg zoompan `on` reset with image2 input.

## Files
- `specs/004-video-enhancement/` — 5 spec files (spec, plan, research, data-model, tasks)
- `piper_models/` — 2 voice models (lessac female, libritts_r male) + JSON configs
- `src/holodeck/agents/audio/voice_synthesis.py` — Piper TTS integration, multi-voice casting, gTTS fallback
- `src/holodeck/agents/video/character_renderer.py` — `render_face()`, `render_clothing()`, `render_hair()`, `render_accessory()`
- `src/holodeck/agents/video/svg_templates.py` — `character_silhouette()` dispatches to character_renderer; `scene_background()` supports `depth` param
- `src/holodeck/agents/video/frame_renderer.py` — Multi-character frames + lip sync via `character_visuals` context key
- `src/holodeck/agents/video/video_assembler.py` — Two-pass smooth zoom, `_COLOR_PRESETS`, `_resolve_color_filter()`, `_build_camera_move_filter()`, preview mode
- `src/holodeck/agents/video/ffmpeg_utils.py` — Builders for concat, audio mix, pitch shift
- `src/holodeck/agents/audio/sfx_library.py` — SFXRegistry (load, search, get_ambience)
- `src/holodeck/agents/audio/sfx_matcher.py` — SFXMatcher (parse SoundDesigner, match cues)
- `src/holodeck/agents/audio/audio_mixer.py` — AudioMixer (FFmpeg amix per-scene mixing, concat)
- `sfx_library/` — 130+ SFX MP3s in category subdirs
- `sfx_library/index.json` — Tag-indexed library manifest
- `scripts/download_sfx.py` — TrekCore SFX downloader
- `scripts/build_sfx_index.py` — Index builder with auto-tagging
- `tests/unit/test_svg_templates.py` — 65 tests
- `tests/unit/test_video_assembler.py` — 45 tests
- `tests/unit/test_ffmpeg_utils.py` — 23 tests
- `tests/unit/agents/audio/test_voice_synthesis.py` — 20 tests
- `tests/unit/test_sfx_library.py` — 8 tests
- `tests/unit/test_sfx_matcher.py` — 7 tests
- `tests/unit/test_audio_mixer.py` — 7 tests
- `tests/integration/test_media_pipeline.py` — 11 tests
- `tests/integration/test_sfx_pipeline.py` — 7 tests
- `tests/e2e/test_media_produce.sh` — smoke test
