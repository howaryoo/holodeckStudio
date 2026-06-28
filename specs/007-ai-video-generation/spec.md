# Feature Specification: AI-Enhanced Video Generation

**Feature Branch**: `007-ai-video-generation`
**Created**: 2026-06-28
**Status**: Draft
**Input**: SVG-only rendering is the bottleneck — characters are geometric shapes, backgrounds are flat gradients, no photorealism despite rich audio (ElevenLabs) and smooth camera. User wants AI models (free tier preferred, paid acceptable) to replace or augment rendering.

**Goal**: Transform output from "watchable indie animation" to "compelling visual story" by injecting AI-generated imagery at key pipeline stages. Keep the existing SVG pipeline as fallback. Maintain zero-GPU constraint where possible (cloud inference only).

**Success Criteria**:
- Character portraits are photorealistic or stylized illustrations (not geometric SVGs)
- Scene backgrounds are AI-generated from scene descriptions (not flat color + SVG props)
- AI-generated elements composite correctly with existing frame pipeline (camera moves, subtitles, transitions)
- Free-tier or low-cost operation: < $5 per short film (< 3 min)
- Graceful degradation: if AI provider is unavailable or budget exhausted, fall back to SVG rendering
- Optional frame upscaling (2x) and/or frame interpolation for smoother motion
- Provider abstraction so swapping models (Replicate → Stability → local) is a config change, not a code change

**Non-Goals**:
- No real-time generation (pipeline remains offline/batch)
- No full AI video generation models (Runway Gen-3, Pika 2.0) unless they offer a compelling free tier — research phase will evaluate
- No 3D models, skeletal animation, or game engine rendering
- No video inpainting / object removal
- No training or fine-tuning custom models (off-the-shelf only)

**Constraints**:
- Must integrate into existing pipeline (stages 20-22, context dict, agent pattern)
- Must support SVG fallback for every AI feature (feature parity maintained)
- Provider selection via environment variable (e.g., `IMAGE_PROVIDER=replicate|stability|huggingface|svgonly`)
- No GPU required on the pipeline host — all inference is cloud API
- API keys set via environment variables (never in code or DB)
- Token/credit budgets configurable per production run

## Clarifications (to be resolved in research phase)

- Q: Character consistency — how to ensure same character looks the same across frames? → A: Use consistent seed + prompt generation per character; consider IP-Adapter or face-consistency if quality demands it.
- Q: Compositing approach — how to layer AI characters on AI backgrounds? → A: Generate per-element transparent PNGs (character on alpha, background as JPG), composite with FFmpeg overlay or ImageMagick. Preserves existing camera move pipeline.
- Q: Frame rate / cost tradeoff — generating 720 frames for a 30s video at 24fps? → A: Research phase: evaluate background-only AI (1 gen per scene), character portraits every N frames with interpolation, or full per-frame generation with budget cap.
- Q: Which providers to support first? → A: Research phase: evaluate Replicate (free credits, broad model selection), Stability AI (dedicated free tier), HuggingFace Inference API (free, rate-limited). Single provider for MVP, easily swappable.

## User Scenarios

1. User generates video → characters look like real people or consistent illustrated style (not SVG stick figures)
2. User generates video → backgrounds match scene descriptions (not colored rectangles with SVG props)
3. User sees smooth character motion even at low frame rates (AI frame interpolation)
4. User runs pipeline without API key → gets normal SVG output (graceful degradation)
5. User hits API budget limit mid-generation → existing frames render with SVG fallback, pipeline completes
6. User swaps `IMAGE_PROVIDER` from `replicate` to `stability` → video generates identically with different model backend
