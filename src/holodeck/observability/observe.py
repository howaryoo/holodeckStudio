from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from typing import Any

try:
    from langfuse.decorators import observe as _langfuse_observe

    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False


def observe(
    name: str | None = None,
    *,
    as_type: str = "span",
    tags: list[str] | None = None,
) -> Callable:
    if not _LANGFUSE_AVAILABLE:
        def _noop(fn: Callable) -> Callable:
            return fn
        return _noop

    kwargs: dict[str, Any] = {}
    if name:
        kwargs["name"] = name
    if as_type == "generation":
        kwargs["as_type"] = "generation"
    return _langfuse_observe(**kwargs)


def trace_production(
    production_id: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> Any:
    return nullcontext()


def flush() -> None:
    from holodeck.observability.tracing import flush as _flush
    _flush()
