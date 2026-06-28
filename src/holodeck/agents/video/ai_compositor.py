from __future__ import annotations

import logging
import os
import tempfile
from io import BytesIO
from typing import TYPE_CHECKING, Any

from PIL import Image

if TYPE_CHECKING:
    from holodeck.agents.video.image_provider import ImageProvider
    from holodeck.config.settings import Settings

logger = logging.getLogger(__name__)

_MOOD_TO_SCENE: dict[str, str] = {
    "warm": "cozy, warm lighting, golden hour",
    "cool": "cold, blue lighting, overcast",
    "sepia": "vintage, sepia tone, nostalgic",
    "noir": "dark, moody, film noir, high contrast",
    "vivid": "bright, saturated colors, vibrant",
    "neutral": "balanced lighting, natural colors",
}


class AICompositor:
    def __init__(
        self,
        provider: ImageProvider,
        settings: Settings | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._context = context

    def generate_background(
        self,
        scene_id: str,
        location: str,
        mood: str = "neutral",
        style: str = "illustrated",
    ) -> Image.Image | None:
        mood_desc = _MOOD_TO_SCENE.get(mood, _MOOD_TO_SCENE["neutral"])
        base = f"{location}, {mood_desc}, background scene, no characters, wide shot"

        from holodeck.agents.video.image_provider import _build_prompt

        result = self._provider.generate(_build_prompt(base, style))
        if result is None:
            return None

        img: Image.Image = Image.open(BytesIO(result["image_data"])).convert("RGB")
        if self._context is not None:
            self._context.setdefault("ai_background_assets", {})[scene_id] = result
        return img

    def generate_character(
        self,
        char_name: str,
        scene_id: str,
        description: str,
        style: str = "illustrated",
        pose: str = "standing",
        production_id: str = "",
    ) -> Image.Image | None:
        base = (
            f"{char_name}, {description}, full body portrait, "
            f"plain background, {pose}"
        )

        from holodeck.agents.video.image_provider import _build_prompt, _make_seed

        seed = _make_seed(char_name, production_id)
        result = self._provider.generate(
            _build_prompt(base, style),
            seed=seed,
        )
        if result is None:
            return None

        img: Image.Image = Image.open(BytesIO(result["image_data"]))
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if self._context is not None:
            per_scene = self._context.setdefault("ai_character_assets", {}).setdefault(scene_id, {})
            per_scene[char_name] = result
        return img

    def compose_frame(
        self,
        background: Image.Image | None,
        characters: list[tuple[Image.Image | None, int, int, float]],
    ) -> str | None:
        if background is None:
            return None

        bg = background.convert("RGBA")

        for char_img, x, y, scale in characters:
            if char_img is None:
                continue
            w = int(char_img.width * scale)
            h = int(char_img.height * scale)
            resized = char_img.resize((w, h), Image.Resampling.LANCZOS)
            bg.paste(resized, (x, y), mask=resized.split()[3])

        tmp_dir = tempfile.mkdtemp(prefix="ai_frame_")
        out_path = os.path.join(tmp_dir, "composited.png")
        bg.save(out_path, "PNG")
        return out_path
