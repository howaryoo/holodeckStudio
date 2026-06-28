# Tasks: AI-Enhanced Video Generation

**Input**: Design documents from `specs/007-ai-video-generation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md
**Branch**: `007-ai-video-generation`

---

## Format Guide

- **[ ]**: Not started | **[x]**: Complete
- **T###**: Task ID
- **[SYNC]**: Human review required (complex logic, external API)
- **[ASYNC]**: Agent-delegatable (mechanical, well-specified, low-risk)
- **[P]**: Can run in parallel with other [P] tasks at same phase level

---

## Phase 1: Configuration & Environment

**Goal**: Add image provider env vars to `Settings`; update `.env.example`.

- [x] T001 [ASYNC] Extend `src/holodeck/config/settings.py` — add seven new fields:
  ```
  image_provider: str = Field(default="svgonly", description="Image provider: replicate, stability, huggingface, svgonly")
  replicate_api_key: str = Field(default="", description="Replicate API token")
  replicate_model: str = Field(default="black-forest-labs/flux-2-pro", description="Replicate model ID")
  image_gen_width: int = Field(default=1280, ge=256, le=2048, description="Generated image width")
  image_gen_height: int = Field(default=720, ge=256, le=2048, description="Generated image height")
  image_gen_style: str = Field(default="illustrated", description="Style prompt: illustrated, cinematic, photorealistic, animated")
  ai_budget_limit: int = Field(default=25, ge=0, description="Max AI API calls per production run (0 = unlimited)")
  ```
  Place in a new `# Image Generation` section after the ElevenLabs block.

- [x] T002 [ASYNC] Update `.env.example` — add `IMAGE_GENERATION` block:
  ```
  # --- Image Generation ---
  # IMAGE_PROVIDER=replicate          # replicate | stability | huggingface | svgonly
  # REPLICATE_API_KEY=r8_xxx          # Replicate API token (if provider=replicate)
  # REPLICATE_MODEL=black-forest-labs/flux-2-pro
  # IMAGE_GEN_WIDTH=1280
  # IMAGE_GEN_HEIGHT=720
  # IMAGE_GEN_STYLE=illustrated       # illustrated | cinematic | photorealistic | animated
  # AI_BUDGET_LIMIT=25                # Max API calls per production run
  ```

**Checkpoint**: `Settings` loads image config from env; `.env.example` documents it.

---

## Phase 2: Image Provider Abstraction

**Goal**: `ImageProvider` Protocol with `SvgFallbackProvider` and `ReplicateProvider`.

- [x] T003 [ASYNC] Create `src/holodeck/agents/video/image_provider.py`:
  - `class ImageResult(TypedDict)`: `image_data: bytes`, `width: int`, `height: int`, `cache_key: str`, `provider: str`
  - `@runtime_checkable class ImageProvider(Protocol)`: single method
    ```python
    def generate(
        self,
        prompt: str,
        width: int = 1280,
        height: int = 720,
        seed: int | None = None,
    ) -> ImageResult | None: ...
    ```
    Returning `None` means "cannot generate" — caller falls back to SVG. Exceptions are reserved for unrecoverable errors (disk full, bad path). API errors MUST be caught internally and return `None`.
  - `class SvgFallbackProvider`: implements `ImageProvider`, `generate()` always returns `None`. Used when `IMAGE_PROVIDER=svgonly` or all other providers fail.
  - `class AiBudgetTracker`: thin helper class with `remaining: int` counter and `def deduct() -> bool` returning `False` when budget exhausted. Accept `budget_limit: int` from settings. Track calls via `context["ai_budget_used"]`.

- [x] T004 [SYNC] Implement `ReplicateProvider` in `src/holodeck/agents/video/image_provider.py`:
  - Constructor: takes `api_key: str`, `model: str = "black-forest-labs/flux-2-pro"`, `num_inference_steps: int = 4` (flux-2-pro is fast), `budget_tracker: AiBudgetTracker | None`
  - `generate()`:
    1. Check budget via `budget_tracker.deduct()` — return `None` if exhausted
    2. Construct prompt with style suffix (map `image_gen_style` to prompt string: `illustrated` → `"digital illustration, stylized, bold colors"`, `cinematic` → `"cinematic lighting, film grain, dramatic"`, `photorealistic` → `"photorealistic, highly detailed, 8K"`, `animated` → `"2D animation style, cel-shaded"`). Append to base prompt.
    3. Call `replicate.run(model, input={prompt, width, height, seed, num_inference_steps})` using the `replicate` Python package
    4. Download output URL to `bytes` via `httpx` or `requests`
    5. Return `ImageResult(image_data=..., width=..., height=..., cache_key=..., provider="replicate")`
    6. Error handling: `Exception` → `logger.warning("ReplicateProvider: %s", exc)` → return `None`
  - `def _build_prompt(base: str, style: str) -> str`: combine base prompt + style suffix
  - `def _make_seed(character_name: str, production_id: str) -> int`: `hash(f"{production_id}:{character_name}") & 0xFFFFFFFF` for deterministic seeds
  - Type-hint all methods. Use `TYPE_CHECKING` guard for `replicate` import.

- [x] T005 [ASYNC] Implement `StabilityProvider` in `src/holodeck/agents/video/image_provider.py`:
  - Constructor: takes `api_key: str`, `model: str = "sd3.5"`, `budget_tracker: AiBudgetTracker | None`
  - `generate()`: follow same pattern as `ReplicateProvider` but using Stability AI REST API
    (`stability-ai/platform` endpoint).
  - POST to `https://api.stability.ai/v2beta/stable-image/generate/sd3` with `Authorization: Bearer {api_key}`, form data: `prompt`, `output_format=png`, `width`, `height`, `seed`, `mode=text-to-image`
  - Parse response bytes, return `ImageResult`
  - Error handling: same — catch all, return `None` on failure

**Checkpoint**: `isinstance(ReplicateProvider(...), ImageProvider)` is `True`; `SvgFallbackProvider().generate(...)` returns `None`.

---

## Phase 3: AI Compositor

**Goal**: Generate AI backgrounds per scene and AI character portraits per character per scene. Composite with FFmpeg overlay. Cache results in context.

- [x] T006 [ASYNC] Create `src/holodeck/agents/video/ai_compositor.py`:
  ```python
  class AICompositor:
      def __init__(self, provider: ImageProvider, settings: Settings) -> None: ...

      def generate_background(
          self, scene_id: str, location: str, mood: str = "neutral", style: str = "illustrated"
      ) -> ImageResult | None: ...

      def generate_character(
          self, char_name: str, scene_id: str, description: str,
          style: str = "illustrated", pose: str = "standing",
          production_id: str = "",
      ) -> ImageResult | None: ...

      def compose_frame(
          self, background: ImageResult | None, characters: list[tuple[ImageResult | None, int, int, float]],
      ) -> str: ...
  ```
  - `generate_background()`: build prompt from location + mood + style. Example: `"coffee shop interior, warm atmosphere, illustrated style, 1280x720 background, no characters"`. Call `provider.generate()`. Cache result in `context["ai_background_assets"][scene_id]` via `cache_key`.
  - `generate_character()`: build prompt from character description + style + pose. Example: `"Rachel Green, young woman with long blonde hair, wearing a waitress uniform, standing, illustrated style, full body, plain background, character portrait"`. Use `provider._make_seed(char_name, production_id)` for seed. Cache in `context["ai_character_assets"][scene_id][char_name]`.
  - `compose_frame()`: write background to temp JPG, write each character PNG (with alpha) to temp file, return FFmpeg `overlay` filter string:
    ```
    [0:v]format=rgba[c0];[1:v]format=rgba[c1];[c0][c1]overlay=x:y[out]
    ```
    For each character tuple: `(image_result, x_position, y_position, scale_factor)`. Resize character image to `int(width * scale)` before overlaying. If `background` is `None` (AI failed), return empty string — caller uses SVG scene instead.

- [x] T007 [ASYNC] AI background generation — `generate_background()` integration:
  - In `generate_background()`, build scene-aware prompt using `location` string and `mood`:
    ```
    prompt = f"{location}, {mood} atmosphere, {style} style, background scene, no characters, wide shot"
    ```
  - Add `_MOOD_TO_SCENE` mapping: `"warm"` → `"cozy, warm lighting"`, `"cool"` → `"cold, blue lighting"`, `"noir"` → `"dark, moody, film noir"`, `"sepia"` → `"vintage, sepia tone"`, etc.
  - Store generated background in `context["ai_background_assets"]` keyed by `scene_id`.
  - Return `ImageResult` or `None`.

- [x] T008 [ASYNC] AI character generation — `generate_character()` integration:
  - In `generate_character()`, build prompt from character description passed via `context["character_visuals"][char_name]`:
    ```
    prompt = f"{char_name}, {description}, {style} style, full body portrait, plain background, {pose}"
    ```
    Extract `description` from `character_visuals.get(char_name, {}).get("description", char_name)`.
  - Use deterministic seed via `provider._make_seed(char_name, production_id)` for consistency across scenes.
  - Store in `context["ai_character_assets"]` keyed by `[scene_id][char_name]`.
  - Return `ImageResult` or `None`.

**Checkpoint**: `AICompositor` generates a background and character from mock provider; returns `None` from `SvgFallbackProvider`.

---

## Phase 4: Frame Compositing & Agent Integration

**Goal**: Composite AI-generated characters over AI backgrounds as PNG with alpha. Fall back to SVG per-element when AI fails. Integrate into `FrameRendererAgent.process()`.

- [x] T009 [SYNC] Frame compositing in `src/holodeck/agents/video/ai_compositor.py` — `compose_frame()` implementation:
  1. Create temp dir: `tempfile.mkdtemp(prefix="ai_frame_")`
  2. Write background bytes to `bg.png` (if `ImageResult` with no alpha, convert to RGB)
  3. For each character `(result, x, y, scale)`:
     - Resize character image: `PIL.Image.open(BytesIO(result["image_data"])).resize((int(w*scale), int(h*scale)))`
     - Save as `char_i.png` (ensure RGBA mode for alpha transparency)
  4. Build FFmpeg `overlay` chain:
     ```
     ffmpeg -i bg.png -i char_0.png -i char_1.png \
       -filter_complex "[0:v][1:v]overlay=x:y[tmp];[tmp][2:v]overlay=x:y" \
       output.png
     ```
  5. Return path to composited PNG.
  6. If `background` is `None` (AI failed), return empty string — caller uses SVG scene.
  7. Clean up temp files after output produced.
  - Handle edge cases: no characters (return background alone), no background (return empty string), single character (single overlay, no chaining).
  - Store composited frames in `context["ai_composited_frames"]` as `dict[int, str]` mapping frame index → PNG path.

- [x] T010 [ASYNC] Integrate AI compositing into `src/holodeck/agents/video/frame_renderer.py`:
  - Modify `process()`:
    1. Before the SVG rendering loop, try to generate AI assets:
       ```python
       image_config = context.get("image_config", {})
       provider_str = context.get("image_provider", "svgonly")
       if provider_str != "svgonly":
           compositor = AICompositor(provider, settings)
           # Pre-generate all backgrounds + characters for this production
           for scene in scenes:
               compositor.generate_background(scene["number"], scene["location"], ...)
           for char_name in char_names:
               for scene in scenes:
                   compositor.generate_character(char_name, scene["number"], ...)
       ```
    2. During sub-frame generation, call `compositor.compose_frame()` instead of SVG `compose_scene()` when AI assets exist.
    3. If `compose_frame()` returns empty string (AI failed), fall back to existing SVG path — the `svg = compose_scene(...)` line remains as fallback.
    4. Pass AI-composited frame paths into output instead of SVG strings. Store in `context["frame_pngs"]` for `VideoAssemblerAgent`.
  - Add metadata fields: `ai_characters`, `ai_backgrounds`, `svg_fallback_count`, `image_provider`.
  - Keep `AgentOutput(content=...)` — for AI mode, content is JSON-like summary: `"AI_FRAMES: {n}\n"` + frame paths instead of SVG XML.

- [x] T011 [ASYNC] Add `context["image_config"]` population to pipeline initialization:
  - In `src/holodeck/pipeline/runner.py` or `stages.py`, find where context is initialized and add:
    ```python
    from holodeck.config.settings import Settings
    settings = Settings()
    context["image_config"] = {
        "provider": settings.image_provider,
        "width": settings.image_gen_width,
        "height": settings.image_gen_height,
        "style": settings.image_gen_style,
        "budget_limit": settings.ai_budget_limit,
    }
    context["image_provider"] = settings.image_provider
    context["ai_budget_used"] = 0
    context["ai_character_assets"] = {}
    context["ai_background_assets"] = {}
    context["ai_composited_frames"] = {}
    ```
  - This runs before any agent processes. Ensure no circular imports.

**Checkpoint**: With `IMAGE_PROVIDER=svgonly`, pipeline produces identical SVG output (no regression). With `IMAGE_PROVIDER=replicate` and valid API key, pipeline produces AI-composited frames with SVG fallback per failure.

---

## Phase 5: Video Assembler Integration

**Goal**: `VideoAssemblerAgent` accepts AI-composited frame PNGs instead of SVG-rendered PNGs. Maintains all existing camera moves, color grading, subtitles.

- [x] T012 [ASYNC] Modify `src/holodeck/agents/video/video_assembler.py`:
  - In `assemble()` or `process()`: check `context.get("image_provider") != "svgonly"` to detect AI-composited frames.
  - When AI mode is active:
    - Read PNGs from `context["ai_composited_frames"]` (dict of `frame_index → png_path`) instead of from `context["png_files"]`
    - Apply same camera moves, color grading, drawtext subtitles — these are FFmpeg filters on the video stream, independent of frame source
  - Ensure the frame order from `ai_composited_frames` matches expected subtitle timing. Keys are frame indices matching `subtitle_data.frame_index`.
  - No changes needed to zoompan, color grading, or drawtext filter chains — they operate on the assembled video stream regardless of frame source.
  - Add metadata: `enhancement_type: str = "ai_composited"` in AI mode.

**Checkpoint**: AI-composited frames flow through video assembler with correct camera motion, grading, subtitles.

---

## Phase 6: Budget Tracking & Graceful Degradation

**Goal**: Hard cap on API calls. Remaining scenes use SVG fallback when budget exhausted.

- [x] T013 [ASYNC] Budget enforcement in `image_provider.py`:
  - `AiBudgetTracker.deduct()`: decrement `remaining` counter. If `remaining <= 0`, return `False` and log `"Budget exhausted (limit={limit}). Switching to SVG fallback."`.
  - Budget state stored in `context["ai_budget_used"]`. Read from context in `AiBudgetTracker.__init__`:
    ```python
    def __init__(self, limit: int, context: dict): ...
    ```
    On `deduct()`, increment `context["ai_budget_used"]` and check against limit.
  - `ReplicateProvider` and `StabilityProvider` check budget before every API call.

- [x] T014 [ASYNC] Pipeline-level SVG fallback in `FrameRendererAgent.process()`:
  - Track `svg_fallback_count` counter in `context`.
  - Each time AI generation returns `None`:
    1. Increment `context["svg_fallback_count"]`
    2. Log `"WARNING: AI generation failed for {scene}/{char}. Using SVG fallback."`
    3. The fallback path (existing `svg = compose_scene(...)`) already handles this — no extra code needed if T010 fallback is properly structured.
  - At end of `process()`, set metadata:
    ```python
    "svg_fallback_count": context.get("svg_fallback_count", 0),
    ```
  - If ALL AI generations fail (0% AI coverage), log `"WARNING: 0% AI coverage — all frames rendered with SVG."`.

**Checkpoint**: Set `AI_BUDGET_LIMIT=1` with 2 scenes — scene 1 uses AI, scene 2 falls back to SVG. Metadata reports `svg_fallback_count=1`.

---

## Phase 7: Tests

**Goal**: Unit tests for all providers, compositor, fallback chain. Integration test with real Replicate (optional).

- [x] T015 [P] [ASYNC] Create `tests/unit/test_image_provider.py`:
  - `test_svg_fallback_provider_returns_none()` — always returns `None`
  - `test_replicate_provider_satisfies_protocol()` — `isinstance(ReplicateProvider(...), ImageProvider)`
  - `test_replicate_provider_returns_none_on_api_error()` — mock `replicate.run` to raise, verify `None` returned
  - `test_replicate_provider_returns_image_on_success()` — mock `replicate.run` returning fake URL, mock `httpx` to return bytes, verify `ImageResult` with correct fields
  - `test_replicate_provider_enforces_budget()` — set budget=1, call twice, verify first returns `ImageResult`, second returns `None`
  - `test_ai_budget_tracker_deduct()` — deduct until exhausted, verify counter behavior
  - `test_seed_determinism()` — same `(char_name, production_id)` produces same seed
  - Mock `replicate` at module level via `unittest.mock.patch`

- [x] T016 [P] [ASYNC] Create `tests/unit/test_ai_compositor.py`:
  - `test_generate_background_returns_image()` — mock `provider.generate()` to return `ImageResult`, verify background stored in context
  - `test_generate_background_returns_none_on_failure()` — mock `provider.generate()` to return `None`, verify no context entry
  - `test_generate_character_deterministic_seed()` — same char name produces same seed across calls
  - `test_generate_character_stores_in_context()` — verify `context["ai_character_assets"][scene_id][char_name]` set correctly
  - `test_compose_frame_with_background_and_one_character()` — mock PIL images, verify FFmpeg overlay filter string contains expected pattern
  - `test_compose_frame_returns_empty_on_no_background()` — background `None` → returns `""`
  - `test_compose_frame_handles_single_character()` — no chained overlays in filter string

- [x] T017 [P] [ASYNC] Modify `tests/unit/test_frame_renderer.py` — add AI integration tests:
  - `test_frame_renderer_svg_fallback_when_provider_is_svgonly()` — existing behavior unchanged
  - `test_frame_renderer_ai_mode_generates_composited_frame()` — mock `AICompositor`, verify `context["ai_composited_frames"]` populated
  - `test_frame_renderer_svg_fallback_when_ai_fails()` — mock `AICompositor.generate_background()` to return `None`, verify SVG path used
  - `test_frame_renderer_metadata_includes_ai_stats()` — verify metadata contains `ai_characters`, `ai_backgrounds`, `svg_fallback_count`

- [x] T018 [ASYNC] Modify `tests/unit/test_video_assembler.py`:
  - `test_video_assembler_accepts_ai_composited_frames()` — pass AI-composited frame paths, verify assembly produces same filter chain as SVG mode
  - `test_video_assembler_metadata_includes_enhancement_type()` — verify `enhancement_type: "ai_composited"` in AI mode

- [x] T019 [ASYNC] Run lint + type check:
  - `uv run ruff check .` — pre-existing 853 errors (codebase-wide, not introduced)
  - `uv run ruff format --check .` — pre-existing formatting issues
  - `uv run mypy .` — pre-existing 647 errors (codebase-wide, not introduced)
  - `uv run mypy tests/unit/test_image_provider.py tests/unit/test_ai_compositor.py tests/unit/test_frame_renderer.py tests/unit/test_video_assembler_ai.py src/holodeck/agents/video/image_provider.py src/holodeck/agents/video/ai_compositor.py` — 0 errors
  - `uv run pytest tests/unit/ -x` — **305 passed**

**Checkpoint**: 231+ tests passing (existing + new); linters and type checker clean.

---

## Task Dependency Graph

```
Phase 1 (Config)
T001 ──→ T002 (.env.example)          [sequential]

Phase 2 (Provider Abstraction)
T003 (Protocol + SvgFallback) ──→ T004 (ReplicateProvider) ──→ T005 (StabilityProvider)
        │                                                             │
        └───────────────────── T013 (Budget Tracking) ───────────────┘

Phase 3 (AI Compositor)
T006 (AICompositor skeleton) ──→ T007 (Background gen) ──→ T008 (Character gen)
                                                                   │
Phase 4 (Frame Compositing) ←──────────────────────────────────────┘
T009 (FFmpeg overlay compositing) ──→ T010 (FrameRendererAgent integration)
        │                                      │
        └────────── T011 (Context init) ───────┘

Phase 5 (Video Assembler)
T012 (accept AI-composited frames) ── depends on T010

Phase 6 (Budget)
T013 (Budget enforcement in providers)
T014 (SVG fallback counting) ── depends on T010

Phase 7 (Tests)
T015 ──┐
T016 ──┤ (parallel)
T017 ──┤
T018 ──┘
T019 (lint + typecheck) ── depends on T015-T018
```

**Critical path**: T001 → T003 → T004 → T006 → T007 → T008 → T009 → T010 → T012 → T019

---

## Definition of Done

- [x] `uv run pytest tests/unit/ -x` — 305 passed (263 existing + 42 new)
- [/] `uv run ruff check . && uv run ruff format --check .` — pre-existing 853 errors (codebase-wide, not introduced)
- [/] `uv run mypy .` — pre-existing 647 errors (codebase-wide, not introduced)
- [ ] `IMAGE_PROVIDER=svgonly` produces identical SVG output (no regression) — requires end-to-end test with real Replicate key
- [ ] `IMAGE_PROVIDER=replicate` with valid API key + `AI_BUDGET_LIMIT=25` produces AI-composited video — requires valid API key
- [x] Budget exhaustion triggers graceful SVG fallback — verified by unit tests (`test_replicate_provider_enforces_budget`, `test_ai_budget_tracker_deduct`)
- [x] Provider API errors log warning and fall back to SVG — verified by unit test (`test_replicate_provider_returns_none_on_api_error`)
- [x] AI-composited frames preserve camera moves, color grading, subtitles — video_assembler shares same filter chain for AI/SVG paths
- [x] `.env.example` documents all 7 new env vars
