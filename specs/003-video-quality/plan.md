# Implementation Plan: Video Quality Improvements

**Branch**: `003-video-quality` | **Date**: 2026-06-10 | **Spec**: [spec.md](./spec.md)
**Input**: User feedback on video output quality from 002-media-generation

## Summary

Improve watchability of generated B&W video using only free-stack tools. 9 tasks across 3 phases: audio+subtitles, scene transitions, richer visuals.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FFmpeg (xfade, drawtext, asetrate), ImageMagick (convert), gTTS, standard library (subprocess, re)
**Storage**: In-memory context dict for subtitle data; temp files for scene segments
**Testing**: pytest (unit for svg_templates, ffmpeg_utils; integration for full flow)
**Target Platform**: Linux (same as existing pipeline)
**Performance Goals**: Video encoding time ≤ 2× audio duration; file size increase ≤ 5× current (from new frames + subtitles)
**Constraints**: $0 cost, FFmpeg/ImageMagick/gTTS only, backward compatible pipeline, no new external dependencies
**Scale/Scope**: 9 tasks across 3 phases — audio pitch + subtitles → scene transitions → richer visuals

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First Development | ✅ PASS | SVG manipulation in Python, FFmpeg via subprocess |
| II. Zen of Python Philosophy | ✅ PASS | Explicit new functions, no silent failures |
| III. Single Responsibility | ✅ PASS | Each task modifies one agent/module |
| IV. Open/Closed & Liskov Substitution | ✅ PASS | Agents unchanged at interface level; new filters added |
| V. Dependency Inversion & Interface Segregation | ✅ PASS | No new agent dependencies |
| Technology Standards | ✅ PASS | Existing ruff/mypy/pytest |
| Development Workflow | ✅ PASS | Test-first for new functions |

**Result**: ALL GATES PASS. No violations to justify.

## Project Structure

```
specs/003-video-quality/
├── plan.md        # This file
├── research.md    # Technology research
├── spec.md        # Feature specification
└── tasks.md       # Task breakdown
```

## Phases & Dependencies

### Phase 1: Audio & Subtitles (3 tasks, parallel)
- T087: Per-character audio pitch shift (ffmpeg_utils)
- T088: Subtitle sync data (frame_renderer → context)
- T089: Burn subtitles via drawtext (video_assembler)

### Phase 2: Scene Transitions (2 tasks, sequential)
- T090: Split video into scene segments (video_assembler)
- T091: Join segments with xfade crossfade (video_assembler)

### Phase 3: Richer Visuals (4 tasks, parallel)
- T092: Environment props from story context (svg_templates)
- T093: Character silhouette detail pass (svg_templates)
- T094: Per-character animation frames (frame_renderer)
- T095: Sub-frame animation via FFmpeg concat (video_assembler)

## Implementation Order

```
Phase 1                          Phase 2                Phase 3
T087 ────┐                       T090 ────┐             T092 ────┐
T088 ────┤  (parallel Phase 1)   T091 ────┤  (sequential) T093 ────┤  (parallel)
T089 ────┘                                │              T094 ────┤
                                          │              T095 ────┘
                                          ▼
                                   (depends on Phase 1
                                    for subtitle timing)

Phase 3 can run in parallel with Phase 1+2 since they modify different modules.
```

## Risk Assessment

- xfade with >2 segments requires cascaded filter chains — test with 3+ scenes
- Subtitle timing requires mapping dialogue file durations to scene offsets
- SVG animation sub-frames increase video size ~N× — keep N ≤ 5 per dialogue line
- All tasks are ASYNC (deterministic code, well-defined)

## Total: 9 tasks
