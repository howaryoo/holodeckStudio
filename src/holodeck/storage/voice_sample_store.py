from __future__ import annotations

import json
import subprocess
from pathlib import Path

from holodeck.config.settings import Settings
from holodeck.storage.object_store import MinIOObjectStore

_SUPPORTED_FORMATS = {"mp3", "wav", "ogg", "flac"}
_MIN_DURATION = 10.0
_MAX_DURATION = 600.0


def validate_audio_file(file_path: str) -> tuple[float, str]:
    """Validate audio file format and duration using ffprobe.

    Returns (duration_seconds, format_name) on success.
    Raises ValueError with a descriptive message on validation failure.
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,format_name",
            "-of", "json",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"ffprobe failed on '{file_path}': {result.stderr.strip()}")

    try:
        probe = json.loads(result.stdout)
        fmt = probe["format"]
        duration = float(fmt["duration"])
        raw_format = fmt["format_name"]
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not parse ffprobe output for '{file_path}': {exc}") from exc

    # Normalise comma-separated format strings (e.g. "mp3,id3v2") to the first token
    detected = raw_format.split(",")[0].strip().lower()

    # Map ffprobe format names to our canonical names
    format_map = {
        "mp3": "mp3",
        "wav": "wav",
        "ogg": "ogg",
        "flac": "flac",
        "opus": "ogg",
        "vorbis": "ogg",
    }
    canonical = format_map.get(detected, detected)
    if canonical not in _SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported audio format '{detected}' in '{file_path}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_FORMATS))}"
        )

    if not (_MIN_DURATION <= duration <= _MAX_DURATION):
        raise ValueError(
            f"Audio duration {duration:.1f}s is outside the allowed range "
            f"[{_MIN_DURATION}s, {_MAX_DURATION}s]"
        )

    return duration, canonical


async def upload_voice_sample(
    file_path: str,
    bible_id: object,
    character_name: str,
    settings: Settings | None = None,
) -> str:
    """Upload a local audio file to MinIO and return the object path.

    Returns the MinIO object key (not including bucket name).
    """
    cfg = settings or Settings()
    store = MinIOObjectStore(
        endpoint=cfg.minio_endpoint,
        access_key=cfg.minio_access_key,
        secret_key=cfg.minio_secret_key,
        secure=cfg.minio_secure,
    )

    path = Path(file_path)
    ext = path.suffix.lstrip(".").lower() or "mp3"
    char_slug = character_name.lower().replace(" ", "_")
    object_key = f"voice-samples/{bible_id}/{char_slug}/sample.{ext}"

    data = path.read_bytes()
    content_type_map = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
    }
    content_type = content_type_map.get(ext, "application/octet-stream")

    await store.put(cfg.minio_bucket, object_key, data, content_type=content_type)
    return object_key
