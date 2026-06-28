# Implementation Plan: AI-Enhanced Video Generation

**Branch**: `007-ai-video-generation` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)
**Input**: User request — improve video output quality using AI models (free tier preferred, paid acceptable)

---

## Summary

Replace SVG-only rendering with AI-generated imagery at key pipeline stages. Three phases: (1) AI characters + backgrounds with compositing, (2) AI upscaling of rendered frames, (3) AI frame interpolation for smooth motion. All features degrade gracefully to SVG fallback. Provider abstraction enables swapping backends (Replicate → Stability → HuggingFace → SVG-only) via environment variable.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `replicate`, `stability-sdk`, `huggingface-hub`, `Pillow` (image compositing)
**Existing Tools**: FFmpeg `overlay` filter, ImageMagick `composite`, existing SVG pipeline
**New Files**: `src/holodeck/agents/video/image_provider.py` (Protocol + providers), `src/holodeck/agents/video/ai_compositor.py` (AI element composition)
**Modified Files**: `frame_renderer.py`, `video_assembler.py`, `svg_templates.py` (fallback path), `config/settings.py` (new env vars)
**Testing**: pytest (unit: mock AI providers, verify fallback logic, verify compositing)
**Target Platform**: Linux CPU (cloud inference only)
**Constraints**: Zero GPU on host; < $0.10 per short film with free-tier credits; SVG fallback for every AI feature
**Scale/Scope**: MVP = 1 provider (Replicate) + SVG fallback; provider swap at config level

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Python-First | ✅ PASS | All provider wrappers in Python; FFmpeg via subprocess |
| II. Zen of Python | ✅ PASS | Explicit provider selection; errors surface as fallback, not silence |
| III. Single Responsibility | ✅ PASS | `ImageProvider` generates; `AICompositor` composites; `FrameRendererAgent` orchestrates |
| IV. Open/Closed | ✅ PASS | `ImageProvider` Protocol allows new providers without modifying agents |
| V. Dependency Inversion | ✅ PASS | Agents depend on Protocol, not concrete providers |
| Technology Standards | ✅ PASS | ruff/mypy/pytest for existing code |
| Development Workflow | ✅ PASS | Test-first for provider wrappers and compositing |

**Result**: ALL GATES PASS.

---

## Project Structure

### Documentation (this feature)

```
specs/007-ai-video-generation/
├── spec.md         # Feature specification
├── research.md     # Provider research + architectural decisions
├── data-model.md   # New entities, context keys, config
├── plan.md         # This file
└── tasks.md        # (generated from plan)
```

### Source Code (repository root)

```
src/holodeck/
├── agents/video/
│   ├── image_provider.py      # NEW: ImageProvider Protocol + ReplicateProvider
│   │                           #      + StabilityProvider + SvgFallbackProvider
│   ├── ai_compositor.py       # NEW: overlay AI chars on AI backgrounds + SVG fallback
│   ├── frame_renderer.py      # MODIFY: inject AI generation before SVG rendering
│   ├── video_assembler.py     # MODIFY: accept AI-enhanced frames; optional upscale/interpolate
│   └── svg_templates.py       # MODIFY: export per-element SVG for fallback composition
├── config/
│   └── settings.py            # MODIFY: IMAGE_PROVIDER, AI_* env vars
tests/
├── unit/
│   ├── test_image_provider.py  # NEW: mock API responses, verify fallback chain
│   ├── test_ai_compositor.py   # NEW: verify correct layer order, alpha handling
│   ├── test_frame_renderer.py  # MODIFY: add AI gen + fallback test cases
│   └── test_video_assembler.py # MODIFY: upscale/interpolation filter tests
└── integration/
    └── test_ai_pipeline.py     # NEW: end-to-end with real provider (optional, requires API key)
```

**Structure Decision**: Single project. All changes additive within existing packages.

---

## Phases & Implementation Order

### Phase 1: AI Image Generation Foundation (Estimated: 4 tasks)

- T001: [ASYNC] Add `IMAGE_PROVIDER` and related env vars to `config/settings.py`
- T002: [ASYNC] Implement `ImageProvider` Protocol + `SvgFallbackProvider` returning None
- T003: [SYNC] Implement `ReplicateProvider` (primary MVP provider — needs API key handling, prompt construction, timeout, budget tracking)
- T004: [ASYNC] Implement `StabilityProvider` and `HuggingFaceProvider` as secondary providers

### Phase 2: Background Generation + Compositing (Estimated: 4 tasks)

- T005: [ASYNC] `AICompositor` — generate AI background per scene from scene description, cache in context
- T006: [ASYNC] `AICompositor` — generate AI character portrait per char per scene (seeded for consistency)
- T007: [SYNC] Frame compositing — character PNG (alpha) over background JPG, with SVG fallback per element
- T008: [ASYNC] Integrate AI compositing into `FrameRendererAgent.process()` — try AI first, fall back to SVG

### Phase 3: Pipeline Integration (Estimated: 3 tasks)

- T009: [ASYNC] Modify `VideoAssemblerAgent` — accept AI-composited frames, maintain zoom/camera/color
- T010: [ASYNC] Budget tracking — count API calls, hard-stop when exhausted, remaining scenes use SVG fallback
- T011: [ASYNC] Unit tests — mock all providers, verify fallback chain at every failure point

### Phase 4: Enhancement Pass — Upscaling (Estimated: 2 tasks)

- T012: [ASYNC] AI upscaling pass — optional 2x upscale of rendered frames via Real-ESRGAN on Replicate
- T013: [ASYNC] Integration — upscale before or after camera moves; resolution management

### Phase 5: Enhancement Pass — Frame Interpolation (Estimated: 2 tasks)

- T014: [ASYNC] AI frame interpolation via FILM (Replicate) or FFmpeg `minterpolate`
- T015: [ASYNC] Integration — interpolate between keyframes to smooth motion; budget-conscious frame selection

---

## Triage Framework: [SYNC] vs [ASYNC] Classification

| Task Category | SYNC | ASYNC | Rationale |
|---------------|------|-------|-----------|
| Provider implementations | 1 | 2 | ReplicateProvider needs API key/auth handling (SYNC); other providers are mechanical clones |
| Compositing logic | 1 | 2 | Frame layout with alpha compositing (SYNC); background/character generation (ASYNC) |
| Pipeline integration | 0 | 2 | Well-defined agent modifications |
| Config/Env vars | 0 | 1 | Additive, well-specified |
| Enhancement passes | 0 | 2 | Wrapping existing API models |
| Tests | 0 | 4 | Mock-based, well-specified |

---

## Risk Assessment

- **API cost overrun**: Budget tracking + hard cap + SVG fallback. User sets `AI_BUDGET_LIMIT=20`, at 20 calls all remaining scenes use SVG.
- **Character inconsistency**: Per-char seed + deterministic prompt. If still inconsistent, add IP-Adapter face consistency in Phase 2 enhancement.
- **API downtime**: Provider health check before generation. Transparent failover to SVG fallback. Warning logged.
- **Latency**: ~2-10s per image generation. Pipeline already async-capable. Pre-generate all assets before frame rendering.
- **API key leaks**: Env vars only. `.env.example` documents required vars. Never logged.
- **Rate limiting**: Retry with exponential backoff (max 3 retries). Fall back to SVG after retries exhausted.
- **SVG fallback visual mismatch**: SVG characters look different from AI characters when mixed in same scene. Acceptable for MVP — fallback degrades gracefully but visibly.

---

## Total: ~15 tasks across 5 phases
