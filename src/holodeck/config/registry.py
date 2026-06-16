from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agno.models.base import Model

_PROVIDER_IMPORTS: dict[str, str] = {
    "openai": "agno.models.openai:OpenAIChat",
    "anthropic": "agno.models.anthropic:Claude",
    "google": "agno.models.google:Gemini",
}


def _import_model_class(provider: str) -> type[Model]:
    if provider not in _PROVIDER_IMPORTS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Available: {', '.join(sorted(_PROVIDER_IMPORTS))}"
        )
    module_path, class_name = _PROVIDER_IMPORTS[provider].rsplit(":", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


_KWARG_MAP: dict[str, dict[str, str]] = {
    "openai": {"api_key": "api_key", "base_url": "base_url"},
    "anthropic": {"api_key": "api_key"},
    "google": {"api_key": "api_key"},
}


def resolve_model(
    spec: str,
    *,
    api_keys: dict[str, str] | None = None,
    base_urls: dict[str, str] | None = None,
) -> Model:
    if "/" not in spec:
        raise ValueError(
            f"Invalid model spec '{spec}'. "
            "Expected format: 'provider/model_id'"
        )

    provider, model_id = spec.split("/", 1)
    model_cls = _import_model_class(provider)
    kwargs: dict[str, str] = {"id": model_id}

    if api_keys and provider in api_keys and api_keys[provider]:
        kwargs["api_key"] = api_keys[provider]
    if base_urls and provider in base_urls and base_urls[provider]:
        kwarg_name = _KWARG_MAP.get(provider, {}).get("base_url")
        if kwarg_name:
            kwargs[kwarg_name] = base_urls[provider]

    return model_cls(**kwargs)


def model_for_agent(
    agent_name: str,
    settings: object | None = None,
) -> Model | None:
    from holodeck.config.settings import Settings

    if settings is None:
        settings = Settings()

    spec = settings.get_model_for_agent(agent_name)
    api_keys: dict[str, str] = {}
    if settings.openai_api_key:
        api_keys["openai"] = settings.openai_api_key
    if settings.anthropic_api_key:
        api_keys["anthropic"] = settings.anthropic_api_key
    if settings.google_api_key:
        api_keys["google"] = settings.google_api_key

    base_urls: dict[str, str] = {}
    if settings.openai_base_url:
        base_urls["openai"] = settings.openai_base_url

    return resolve_model(spec, api_keys=api_keys, base_urls=base_urls)
