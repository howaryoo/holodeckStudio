# Data Model: AI-Enhanced Video Generation

## New Data Entities

### ImageGenerationConfig

Per-production configuration for AI image generation.

```
ImageGenerationConfig {
  provider: str                   // "replicate", "stability", "huggingface", "svgonly"
  model: str                      // e.g. "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
  width: int                      // Output width (default 1280)
  height: int                     // Output height (default 720)
  style: str                      // "photorealistic", "illustrated", "animated", "cinematic"
  seed: int | None                // Fixed seed for reproducibility (None = random)
  num_inference_steps: int        // Quality/speed tradeoff (default 25)
  budget_limit: int | None        // Max API calls per production run
}
```

**Storage**: `context["image_config"]`, generated from env vars + defaults. Not persisted in DB.

### AICharacterAsset

An AI-generated character portrait with alpha channel, used for compositing.

```
AICharacterAsset {
  character_name: str             // Matches character in script
  scene_id: str                   // Scene this asset was generated for
  prompt: str                     // Full prompt used
  seed: int                       // Seed used for generation
  provider: str                   // Which provider generated it
  image_data: bytes               // PNG bytes (RGBA with alpha)
  width: int                      // Image width
  height: int                     // Image height
  cache_key: str                  // MD5 of prompt + seed + provider
  generated_at: str               // ISO timestamp
}
```

**Storage**: In-memory during generation (`context["ai_character_assets"]`), optionally cached to disk for reuse.

### AIBackgroundAsset

An AI-generated scene background, used as backdrop.

```
AIBackgroundAsset {
  scene_id: str                   // Scene identifier
  location: str                   // Location description
  prompt: str                     // Full prompt used
  seed: int                       // Seed used
  provider: str                   // Provider
  image_data: bytes               // JPG or PNG bytes
  width: int                      // Image width
  height: int                     // Image height
  cache_key: str                  // MD5 of prompt + seed + provider
  generated_at: str               // ISO timestamp
}
```

**Storage**: Same pattern as AICharacterAsset.

### GeneratedFrame

An enhanced frame after optional upscaling or interpolation.

```
GeneratedFrame {
  frame_index: int                // Frame number in sequence
  source_png: str                 // Path to original SVG-rendered PNG
  enhanced_png: str               // Path to AI-enhanced/upscaled PNG (if applied)
  upscale_factor: float           // 1.0 (none), 2.0 (2x), etc.
  interpolation: bool             // Whether frame was AI-interpolated
}
```

**Storage**: Temporary files during assembly, not persisted.

## New Context Keys

| Key | Type | Description | Set By |
|-----|------|-------------|--------|
| `image_config` | `ImageGenerationConfig` | Generation config | Pipeline initialization |
| `ai_character_assets` | `dict[str, dict[str, AICharacterAsset]]` | Per-scene, per-character AI portraits | FrameRendererAgent |
| `ai_background_assets` | `dict[str, AIBackgroundAsset]` | Per-scene AI backgrounds | FrameRendererAgent |
| `image_provider` | `str` | Active provider name | Config resolution |
| `ai_budget_used` | `int` | API calls consumed this run | ImageProvider tracking |

## Modified Agent Metadata

### FrameRendererAgent

| Field | Type | Description |
|-------|------|-------------|
| `ai_characters` | `int` | Count of scenes with AI-generated characters |
| `ai_backgrounds` | `int` | Count of scenes with AI-generated backgrounds |
| `svg_fallback_count` | `int` | Count of AI failures → SVG fallback |
| `image_provider` | `str` | Provider used |

### VideoAssemblerAgent

| Field | Type | Description |
|-------|------|-------------|
| `enhancement_type` | `str` | "none", "upscale", "interpolate", "both" |
| `upscale_factor` | `float` | Applied upscale factor |
| `interpolation_fps_multiplier` | `float` | Frame interpolation multiplier |

## New Context Constants

```python
# Default image generation config (from env or defaults)
DEFAULT_IMAGE_CONFIG = {
    "width": 1280,
    "height": 720,
    "style": "cinematic",
    "num_inference_steps": 25,
    "budget_limit": 50,
}

# Provider → default model mapping
DEFAULT_MODELS = {
    "replicate": "black-forest-labs/flux-2-pro",
    "stability": "sd3.5",
    "huggingface": "stabilityai/stable-diffusion-xl-base-1.0",
}

# Style → prompt suffix mapping
STYLE_PROMPTS = {
    "photorealistic": "photorealistic, highly detailed, 8K",
    "illustrated": "digital illustration, stylized, concept art",
    "animated": "2D animation style, bold colors, cel-shaded",
    "cinematic": "cinematic lighting, film grain, dramatic",
}
```
