from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...
    def clear(self) -> None: ...
    def remove(self, key: str) -> bool: ...


class InMemoryBackend:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at = entry.get("expires_at")
        if expires_at is not None and time.monotonic() > expires_at:
            del self._store[key]
            return None
        return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._store[key] = {
            "value": value,
            "expires_at": (time.monotonic() + ttl_seconds) if ttl_seconds else None,
        }

    def clear(self) -> None:
        self._store.clear()

    def remove(self, key: str) -> bool:
        return bool(self._store.pop(key, None))


class FileBackend:
    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self._cache_dir = Path(cache_dir or Path.home() / ".holodeck" / "cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = hashlib.sha256(key.encode()).hexdigest()
        return self._cache_dir / f"{safe}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            expires_at = data.get("expires_at")
            if expires_at is not None and time.time() > expires_at:
                path.unlink(missing_ok=True)
                return None
            return data["value"]
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        path = self._path(key)
        data = {
            "value": value,
            "expires_at": (time.time() + ttl_seconds) if ttl_seconds else None,
            "created_at": time.time(),
        }
        path.write_text(json.dumps(data, default=str, indent=2))

    def clear(self) -> None:
        for f in self._cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)

    def remove(self, key: str) -> bool:
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_keys(self) -> list[str]:
        keys: list[str] = []
        for f in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if "value" in data:
                    keys.append(f.stem)
            except Exception:
                pass
        return keys


def generate_cache_key(
    prompt: str,
    bible_id: str | None = None,
    mode: str = "autonomous",
) -> str:
    normalized = " ".join(prompt.lower().split())
    raw = f"{normalized}|{bible_id or ''}|{mode}"
    return hashlib.sha256(raw.encode()).hexdigest()


_AGENT_CACHE: dict[str, Any] = {}


def agent_cache_key(role: str, prompt: str) -> str:
    return hashlib.sha256(f"{role}||{prompt}".encode()).hexdigest()


def get_cached_agent_result(role: str, prompt: str) -> Any | None:
    return _AGENT_CACHE.get(agent_cache_key(role, prompt))


def set_cached_agent_result(role: str, prompt: str, result: Any, ttl_seconds: int | None = 3600) -> None:
    key = agent_cache_key(role, prompt)
    _AGENT_CACHE[key] = result


def clear_agent_cache() -> None:
    _AGENT_CACHE.clear()


def cached_agent_run(agent_fn, role: str, user_message: str, use_cache: bool = True):
    if use_cache:
        cached = get_cached_agent_result(role, user_message)
        if cached is not None:
            return cached
    result = agent_fn(user_message)
    if use_cache:
        set_cached_agent_result(role, user_message, result)
    return result


class PipelineCache:
    def __init__(self, backend: CacheBackend | None = None) -> None:
        self._backend = backend or FileBackend()

    def get(self, prompt: str, bible_id: str | None = None, mode: str = "autonomous") -> dict | None:
        key = generate_cache_key(prompt, bible_id, mode)
        return self._backend.get(key)

    def set(
        self,
        prompt: str,
        bible_id: str | None,
        mode: str,
        result: dict,
        ttl_seconds: int | None = 3600,
    ) -> None:
        key = generate_cache_key(prompt, bible_id, mode)
        self._backend.set(key, result, ttl_seconds=ttl_seconds)

    def clear(self) -> None:
        self._backend.clear()

    def remove(self, prompt: str, bible_id: str | None = None, mode: str = "autonomous") -> bool:
        key = generate_cache_key(prompt, bible_id, mode)
        return self._backend.remove(key)

    @property
    def backend(self) -> CacheBackend:
        return self._backend
