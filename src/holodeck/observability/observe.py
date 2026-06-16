from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from langfuse import observe as _langfuse_observe

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

    kwargs: dict[str, Any] = {"as_type": as_type}
    if name:
        kwargs["name"] = name
    if tags:
        kwargs["tags"] = tags
    return _langfuse_observe(**kwargs)


def trace_production(
    production_id: str,
    session_id: str | None = None,
    user_id: str | None = None,
) -> Any:
    if not _LANGFUSE_AVAILABLE:
        from contextlib import nullcontext
        return nullcontext()

    from langfuse import propagate_attributes

    attrs: dict[str, Any] = {}
    if session_id:
        attrs["session_id"] = session_id
    if user_id:
        attrs["user_id"] = user_id
    attrs["metadata"] = {"production_id": production_id}
    return propagate_attributes(**attrs)


def flush() -> None:
    from holodeck.observability.tracing import flush as _flush
    _flush()
