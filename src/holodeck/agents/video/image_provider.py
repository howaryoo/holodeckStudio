from __future__ import annotations

import hashlib
import logging
from typing import Any, Protocol, TypedDict, runtime_checkable

import httpx

logger = logging.getLogger(__name__)


class ImageResult(TypedDict):
    image_data: bytes
    width: int
    height: int
    cache_key: str
    provider: str


_STYLE_PROMPTS: dict[str, str] = {
    "illustrated": "digital illustration, stylized, bold colors, concept art",
    "cinematic": "cinematic lighting, film grain, dramatic, anamorphic",
    "photorealistic": "photorealistic, highly detailed, 8K, hyperrealistic",
    "animated": "2D animation style, cel-shaded, bold outlines, vibrant",
}


@runtime_checkable
class ImageProvider(Protocol):
    def generate(
        self,
        prompt: str,
        width: int = 1280,
        height: int = 720,
        seed: int | None = None,
    ) -> ImageResult | None: ...


class SvgFallbackProvider:
    def generate(
        self,
        prompt: str,
        width: int = 1280,
        height: int = 720,
        seed: int | None = None,
    ) -> ImageResult | None:
        return None


class AiBudgetTracker:
    def __init__(self, limit: int, context: dict[str, Any] | None = None) -> None:
        self._limit = limit
        self._context = context

    def deduct(self) -> bool:
        if self._limit <= 0:
            return True
        if self._context is not None:
            used = self._context.get("ai_budget_used", 0)
            if used >= self._limit:
                logger.warning(
                    "Budget exhausted (limit=%d). Switching to SVG fallback.",
                    self._limit,
                )
                return False
            self._context["ai_budget_used"] = used + 1
        return True


def _build_prompt(base: str, style: str) -> str:
    suffix = _STYLE_PROMPTS.get(style, _STYLE_PROMPTS["illustrated"])
    return f"{base}, {suffix}"


def _make_seed(character_name: str, production_id: str) -> int:
    h = hashlib.md5(f"{production_id}:{character_name}".encode())  # noqa: S324
    return int.from_bytes(h.digest()[:4], "little")


class ReplicateProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "black-forest-labs/flux-2-pro",
        num_inference_steps: int = 4,
        budget_tracker: AiBudgetTracker | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._num_inference_steps = num_inference_steps
        self._budget_tracker = budget_tracker

    def generate(
        self,
        prompt: str,
        width: int = 1280,
        height: int = 720,
        seed: int | None = None,
    ) -> ImageResult | None:
        if self._budget_tracker is not None and not self._budget_tracker.deduct():
            return None
        from replicate.client import Client

        client = Client(api_token=self._api_key)

        try:
            output = client.run(
                self._model,
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "seed": seed,
                    "num_inference_steps": self._num_inference_steps,
                },
            )
        except Exception as exc:
            logger.warning("ReplicateProvider: run failed for prompt %r: %s", prompt[:60], exc)
            return None

        image_url: str | None = None
        if isinstance(output, list):
            for item in output:
                url = str(item).strip()
                if url.startswith("http"):
                    image_url = url
                    break
        elif isinstance(output, str):
            if output.startswith("http"):
                image_url = output
        else:
            url = str(output).strip()
            if url.startswith("http"):
                image_url = url

        if not image_url:
            logger.warning("ReplicateProvider: no image URL in output: %s", output)
            return None

        try:
            resp = httpx.get(image_url, timeout=60)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("ReplicateProvider: download failed for %s: %s", image_url[:60], exc)
            return None

        cache_key = hashlib.md5(f"{self._model}:{prompt}:{seed}".encode()).hexdigest()  # noqa: S324
        return ImageResult(
            image_data=resp.content,
            width=width,
            height=height,
            cache_key=cache_key,
            provider="replicate",
        )


class StabilityProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "sd3.5",
        budget_tracker: AiBudgetTracker | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._budget_tracker = budget_tracker

    def generate(
        self,
        prompt: str,
        width: int = 1280,
        height: int = 720,
        seed: int | None = None,
    ) -> ImageResult | None:
        if self._budget_tracker is not None and not self._budget_tracker.deduct():
            return None

        try:
            resp = httpx.post(
                "https://api.stability.ai/v2beta/stable-image/generate/sd3",
                headers={"Authorization": f"Bearer {self._api_key}"},
                data={
                    "prompt": prompt,
                    "output_format": "png",
                    "width": width,
                    "height": height,
                    "seed": seed,
                    "mode": "text-to-image",
                },
                timeout=60,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("StabilityProvider: API call failed: %s", exc)
            return None

        cache_key = hashlib.md5(f"{self._model}:{prompt}:{seed}".encode()).hexdigest()  # noqa: S324
        return ImageResult(
            image_data=resp.content,
            width=width,
            height=height,
            cache_key=cache_key,
            provider="stability",
        )
