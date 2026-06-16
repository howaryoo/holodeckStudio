# Implementation Plan: Video Enhancement

**Branch**: `004-video-enhancement` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)
**Input**: User feedback — video is still poor quality after 003-video-quality

## Summary

Transform video from stick-figure demo to watchable short film. 12 tasks across 4 phases: camera + grading → rich characters → piper TTS → scene composition.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FFmpeg (crop, scale, curves, colorbalance, concat), ImageMagick (convert), piper-tts (new), Python standard library
**Storage**: In-memory context dict; piper models cached locally (~150MB for 3 voices)
**Testing**: pytest (unit for SVG templates, FFmpeg filters; integration for full media pipeline)
**Target Platform**: Linux CPU
**Performance Goals**: Video encoding time ≤ 3× audio duration; piper TTS ~2× realtime on CPU
**Constraints**: $0 cost, FFmpeg/ImageMagick/Python only, piper-tts optional (falls back to gTTS), backward compatible pipeline

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First Development | ✅ PASS | SVG manipulation in Python, FFmpeg via subprocess, piper via subprocess |
| II. Zen of Python Philosophy | ✅ PASS | Deterministic SVG generation, composable filters |
| III. Single Responsibility | ✅ PASS | Each task modifies one agent/module |
| IV. Open/Closed & Liskov Substitution | ✅ PASS | Agents unchanged at interface level; fallback to gTTS if piper absent |
| V. Dependency Inversion & Interface Segregation | ✅ PASS | Piper wrapped behind VoiceSynthesisAgent interface |
| Technology Standards | ✅ PASS | ruff/mypy/pytest for existing code |
| Development Workflow | ✅ PASS | Test-first for SVG templates and FFmpeg commands |

**Result**: ALL GATES PASS.

## Project Structure

### Documentation (this feature)

```
specs/004-video-enhancement/
├── plan.md        # This file (/spec.plan command output)
├── research.md    # Phase 0 output (/spec.plan command)
├── data-model.md  # Phase 1 output (/spec.plan command)
├── spec.md        # Feature specification
└── tasks.md       # Phase 2 output (/spec.tasks command - NOT created by /spec.plan)
```

### Source Code (repository root)

```
src/holodeck/
├── agents/
│   ├── video/
│   │   ├── svg_templates.py    # T099-T101, T105: character + background SVG
│   │   ├── character_renderer.py # T099-T101: extracted after Phase 2
│   │   ├── frame_renderer.py    # T104, T106: multi-character + lip-sync
│   │   └── video_assembler.py   # T096-T098: zoom, grade, camera motion
│   └── audio/
│       └── voice_synthesis.py   # T102-T103: piper TTS integration
├── pipeline/
│   ├── orchestrator.py
│   └── runner.py
tests/
├── unit/
│   ├── test_svg_templates.py    # Extended for new SVG features
│   ├── test_ffmpeg_utils.py     # Extended for color grading filters
│   └── test_video_assembler.py  # New: scene grouping + zoompan tests
└── integration/
    └── test_media_pipeline.py   # Extended for piper + multi-char tests
```

**Structure Decision**: Single project (DEFAULT). All changes target existing modules under `src/holodeck/agents/`. No new top-level packages.

## Phases & Dependencies

### Phase 1: Camera & Color (3 tasks, sequential)
- T096: Smooth continuous zoom (single zoompan pass on concatenated video)
- T097: Per-scene color grading (replace fixed B&W with mood-appropriate palette; scene mood sourced from ProductionDesigner stage metadata, default to noir)
- T098: Camera motion — dolly + pan + tilt via crop/scale chain

### Phase 2: Rich Characters (3 tasks, parallel)
- T099: SVG face + facial features (eyes, nose, mouth with open/closed states)
- T100: SVG clothing + body detail (torso shape, neckline, uniform indicators)
- T101: Character accessories + hair styles (parameterized SVG elements)

### Phase 3: Piper TTS (2 tasks, sequential)
- T102: Piper TTS integration (VoiceSynthesisAgent fallback gTTS→piper)
- T103: Multi-voice casting (map character gender to piper voice models)

### Phase 4: Scene Composition (4 tasks, parallel)
- T104: Multi-character SVG frames (active speaker + listeners in same frame)
- T105: Layered backgrounds (foreground/midground/background depth)
- T106: Lip-sync approximation (mouth shape alternating during speech)
- T107: Preview mode — generate lower-res faster for iteration

## Implementation Order

```
Phase 1               Phase 2               Phase 3                Phase 4
T096 ────┐            T099 ────┐            T102 ────┐             T104 ────┐
T097 ────┤ (seq)      T100 ────┤ (parallel)  T103 ────┤ (seq)       T105 ────┤ (parallel)
T098 <────┘           T101 ────┘                       │             T106 ────┤
                                                        │             T107 ────┘
                                                        ▼
                                                  (independent of
                                                   Phase 1,2,4)
```

Phase 1 can run first (fixes the most obvious problem — static video).
Phase 2, 3, 4 are independent and can run in any order after Phase 1.

## Triage Framework: [SYNC] vs [ASYNC] Classification

All 12 tasks are **[ASYNC]** (agent-delegation suitable). No task requires human review:

| Task Category | SYNC | ASYNC | Rationale |
|---------------|------|-------|-----------|
| SVG Templates | 0 | 4 | Pure coordinate math, backward-compatible defaults, no side effects |
| FFmpeg Filters | 0 | 3 | Well-defined CLI arg construction, deterministic I/O |
| Piper TTS | 0 | 2 | CLI subprocess wrapping with transparent fallback |
| Pipeline Integration | 0 | 2 | Context dict reads/writes, no schema changes |
| Preview Mode | 0 | 1 | Conditional early returns, resolution caps |

**Rationale**: No security-critical code, no external API contracts, no state machines, no DB schema changes. Every task has a well-defined input → output transformation with existing test infrastructure covering the pattern.

## Complexity Tracking

No constitution violations to justify. All gates pass.

## Risk Assessment

- **Piper TTS not installed**: VoiceSynthesisAgent falls back to gTTS transparently
- **Piper inference slow on CPU**: Pre-generate audio; pipeline already buffers audio before video assembly
- **Complex SVG frames increase memory**: 50-frame limit (from T095) caps SVG count
- **character\_silhouette() violates SR**: Function accumulates face, clothing, hair, build, accessories — 5 concerns. After T099-T101, extract into `character_renderer.py` with `render_face()`, `render_clothing()`, `render_hair()`, `render_accessory()`. Keep `character_silhouette()` as thin dispatcher for backward compat.
- **Multi-character frames may look cluttered**: Limit to 2 characters per frame max
- **Color grading may look worse than B&W**: Default to B&W when scene mood is unknown
- **Smooth camera may desync from subtitles**: Re-base subtitle timing on output frame timestamps

## Total: 12 tasks
