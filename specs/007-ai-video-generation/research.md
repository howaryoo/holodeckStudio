# Research: AI-Enhanced Video Generation

**Goal**: Replace SVG-only rendering with AI-generated imagery. Evaluate providers, costs, quality, and integration approaches.

---

## Provider Landscape (June 2026)

### Replicate

| Aspect | Detail |
|--------|--------|
| **Free tier** | $5 free credits on signup, no recurring free credits |
| **Pricing** | ~$0.002 per image (SDXL), ~$0.0004 per image (SSD-1B) |
| **Models** | SDXL, Flux, Playground v2, SSD-1B (fast/cheap), Real-ESRGAN (upscale), FILM (frame interpolation) |
| **Latency** | 2-10s per image (SSD-1B: 1-3s) |
| **SDK** | `replicate` Python package, simple API |
| **Pros** | Broad model selection, predictable pricing, fast inference |
| **Cons** | No recurring free tier, pay-as-you-go |

**Cost estimate**: 10 backgrounds + 5 character refs = ~$0.03 per short film. With upscaling + interpolation: ~$0.10.

### Stability AI (Stable Diffusion API)

| Aspect | Detail |
|--------|--------|
| **Free tier** | Yes — 25 API calls/day free (Stability AI Platform) |
| **Pricing** | ~$0.004 per image (SDXL) beyond free tier |
| **Models** | SDXL 1.0, SD3.5, Core |
| **Latency** | 1-5s per image |
| **SDK** | `stability-sdk` Python package OR REST |
| **Pros** | Generous free tier, high quality SD3.5 outpainting |
| **Cons** | Rate-limited on free tier (25/day) |

**Cost estimate**: Free tier covers ~2 short films/day. Beyond that: ~$0.06 per film.

### HuggingFace Inference API

| Aspect | Detail |
|--------|--------|
| **Free tier** | Yes — 30K input chars/day, rate-limited |
| **Pricing** | $0.09/hour serverless (billed per second) |
| **Models** | Thousands — SDXL, FLUX.2, SSD-1B, Real-ESRGAN, etc. |
| **Latency** | 5-20s (free tier queue), 2-5s (paid inference endpoints) |
| **SDK** | `huggingface-hub` Python package |
| **Pros** | Largest model selection, no single-vendor lock |
| **Cons** | Free tier has queue delays, unreliable for production |

**Cost estimate**: Free tier usable for dev/test. Paid: ~$0.05-0.10 per film with dedicated endpoint.

### Together AI

| Aspect | Detail |
|--------|--------|
| **Free tier** | $1 free credits on signup |
| **Pricing** | ~$0.0006 per image (SDXL) |
| **Models** | SDXL, FLUX.1-schnell (fast, cheap) |
| **Latency** | 1-3s |
| **SDK** | REST API (no official Python SDK) |
| **Pros** | Cheapest per-image, fast inference |
| **Cons** | Minimal free credits, limited model selection |

### RunwayML / Pika (Full Video Generation)

| Aspect | Detail |
|--------|--------|
| **Free tier** | Runway: ~125 credits free (gen2), Pika: limited free |
| **Pricing** | Runway: $15/mo (500 credits), Pika: $10/mo (700 credits) |
| **Models** | Gen-3 Alpha, Pika 2.0 |
| **Latency** | 30-90s per 5s clip |
| **SDK** | REST API |
| **Pros** | Full video output (not per-frame), highest quality |
| **Cons** | Expensive per minute, limited control over character consistency, no SVG fallback composition |

**Decision**: Exclude Runway/Pika from MVP. Character consistency is unsolved and cost is 10-100x per-frame generation. Revisit if character consistency improves (e.g., Runway's character reference feature).

---

## Integration Architecture

### Option A: Replace SVG Entirely

Generate each frame as a full AI image. Discard SVG pipeline entirely.

- **Pros**: Highest visual quality, simplest architecture
- **Cons**: Extremely expensive (720 frames × $0.002 = $1.44 per 30s video), no character consistency
- **Verdict**: Rejected — too expensive, no consistency across frames

### Option B: AI Characters + AI Backgrounds + SVG Compositing

Generate character PNGs (transparent background) and background JPGs via AI. Composite with SVG overlays (subtitles, effects) using FFmpeg.

- **Pros**: Cost-effective (1 gen per character per scene + 1 gen per background), character consistency via seed, maintains existing camera move pipeline
- **Cons**: Characters are static per scene (no pose variation), requires alpha-channel generation
- **Verdict**: ✅ SELECTED for MVP

### Option C: AI-Enhanced SVG

Use AI to upscale/fill rendered SVG frames (e.g., "img2img" with low denoising to add detail to SVG output).

- **Pros**: Preserves exact composition, cheaper than full generation
- **Cons**: SVG-to-image artifacts, limited quality improvement
- **Verdict**: Good for post-processing pass (Tier 2 enhancement)

### Option D: Hybrid Frame Generation

Use AI to generate keyframes only, interpolate or morph between them with FFmpeg `minterpolate` or AI frame interpolation (FILM).

- **Pros**: Dramatically reduces gen count, smooth motion
- **Cons**: Complex pipeline, artifacts between keyframes
- **Verdict**: Tier 2 feature — implement after Option B MVP

---

## Feasibility Summary

| Technique | Complexity | Impact | Cost/30s video |
|-----------|-----------|--------|----------------|
| AI backgrounds (1 per scene) | Low | High | ~$0.01-0.05 |
| AI character portraits (1 per char per scene) | Medium | Very High | ~$0.02-0.10 |
| AI upscaling (2x post-process) | Low | Medium | ~$0.02 per film |
| AI frame interpolation | Medium | Medium | ~$0.10 per film |
| Full per-frame AI gen | Very High | Very High | ~$1.50 per film |
| SVG → AI img2img enhancement | Medium | Medium | ~$0.05 per film |

**Recommendation**: Phase 1 — AI backgrounds + AI character portraits per scene. Phase 2 — AI upscaling. Phase 3 — AI frame interpolation.

---

## Key Technical Decisions (Resolved)

### Decision 1: Image Generation Abstraction

**Decision**: `ImageProvider` Protocol with `generate(prompt, size, seed) → bytes` interface. Concrete implementations: `ReplicateProvider`, `StabilityProvider`, `HuggingFaceProvider`, `SvgFallbackProvider`.

**Rationale**: Same pattern as `VoiceSynthesisProvider` from 006-elevenlabs. Provider selected via `IMAGE_PROVIDER` env var. Fallback provider returns None → pipeline uses SVG.

### Decision 2: Character Consistency

**Decision**: Per-character seed + deterministic prompt template. `character_seed = hash(character_name + production_id) & 0xFFFFFFFF`. Prompt template: `"portrait of {name}, {description}, {style}, plain background, full body, {pose}"`.

**Rationale**: Same seed → same character appearance across frames/scenes. No face-consistency model needed for MVP. Style parameter controls aesthetic (photorealistic, illustrated, etc.).

### Decision 3: Background Generation Strategy

**Decision**: One background generation per scene, not per frame. Scene description from ProductionDesigner drives prompt. Background cached in context dict.

**Rationale**: 5-10 scenes per short film → 5-10 API calls. Same background throughout scene. Camera pan/zoom applied via FFmpeg (existing pipeline) over the single AI-generated background.

### Decision 4: Compositing Pipeline

**Decision**: FFmpeg overlay compositing. AI character PNG (alpha) over AI background JPG, with SVG subtitles drawn on top using drawtext. Same assembly flow as existing but with different source images.

**Rationale**: Existing `VideoAssemblerAgent.assemble_segment()` already does multi-layer compositing. Adding `overlay` filter is simpler than new compositing system.

### Decision 5: SVG Fallback Granularity

**Decision**: Per-element fallback. If AI character generation fails, only that character uses SVG for that scene. If AI background fails, only that scene uses SVG background. Never hard-abort.

**Rationale**: Graceful degradation means partial AI coverage still improves overall quality.
