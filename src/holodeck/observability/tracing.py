from __future__ import annotations

from typing import Any

from holodeck.config.settings import Settings

_client: Any | None = None


def setup_tracing(settings: Settings) -> None:
    global _client

    import os

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
        if settings.langfuse_host:
            os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return

    import base64

    from langfuse import get_client as _get_client

    _client = _get_client()

    from openinference.instrumentation.agno import AgnoInstrumentor
    from opentelemetry import trace as trace_api
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    langfuse_auth = base64.b64encode(
        f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}".encode()
    ).decode()

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = (
        f"{settings.langfuse_host}/api/public/otel"
    )
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
        f"Authorization=Basic {langfuse_auth}"
    )

    current_provider = trace_api.get_tracer_provider()
    if not isinstance(current_provider, TracerProvider):
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
        trace_api.set_tracer_provider(tracer_provider=tracer_provider)

    AgnoInstrumentor().instrument()


def get_client() -> Any | None:
    return _client


def flush() -> None:
    if _client is not None:
        _client.flush()
