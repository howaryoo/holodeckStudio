from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from holodeck.storage.object_store import ObjectStore


_CONTENT_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg",
    ".json": "application/json",
}

_MEDIA_BUCKET = "holodeck-media"


def _content_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return _CONTENT_TYPES.get(ext, "application/octet-stream")


class MediaStorage:
    def __init__(self, store: ObjectStore) -> None:
        self._store = store

    async def ensure_bucket(self) -> None:
        """Create holodeck-media bucket if it doesn't exist."""
        existing = await self._store.list(_MEDIA_BUCKET)
        if not existing:
            await self._store.put(
                _MEDIA_BUCKET,
                ".holodeck-init",
                b"",
                "text/plain",
            )

    async def upload_media(
        self,
        production_id: str,
        episode_id: str,
        stage: str,
        filename: str,
        data: bytes,
    ) -> str:
        key = f"productions/{production_id}/{episode_id}/{stage}/{filename}"
        ct = _content_type(filename)
        return await self._store.put(_MEDIA_BUCKET, key, data, ct)

    async def get_media_url(self, path: str) -> bytes:
        return await self._store.get(_MEDIA_BUCKET, path)

    async def list_media(
        self,
        production_id: str | None = None,
        episode_id: str | None = None,
        stage: str | None = None,
    ) -> list[str]:
        prefix = "productions/"
        if production_id:
            prefix += f"{production_id}/"
            if episode_id:
                prefix += f"{episode_id}/"
                if stage:
                    prefix += f"{stage}/"
        return [
            p
            for p in await self._store.list(_MEDIA_BUCKET, prefix)
            if not p.endswith(".holodeck-init")
        ]
