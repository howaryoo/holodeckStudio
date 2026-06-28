from __future__ import annotations

import os
from typing import Any

from holodeck.config.settings import Settings

_client: Any | None = None


def setup_tracing(settings: Settings) -> None:
    global _client

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_host:
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    from langfuse import Langfuse

    _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host or "https://cloud.langfuse.com",
    )


def get_client() -> Any | None:
    return _client


def flush() -> None:
    if _client is not None:
        _client.flush()
