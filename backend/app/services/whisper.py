"""WhisperFlow audio transcription client.

Wraps the OpenAI-compatible /v1/audio/transcriptions endpoint exposed by the
local proxy at 127.0.0.1:31415.  This is the mandatory voice-input layer.
"""
import os
import uuid
import httpx
from pathlib import Path

from ..config import settings


async def transcribe(file_path: Path, language: str | None = None) -> dict:
    """Send an audio file to the proxy and return the full transcription payload."""
    base_url = getattr(settings, "whisper_base_url", None) or "http://127.0.0.1:31415"
    url = f"{base_url}/v1/audio/transcriptions"
    api_key = getattr(settings, "whisper_api_key", None) or settings.llm_api_key
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    files = {"file": (file_path.name, file_bytes, "audio/wav")}
    data = {"model": "whisper-1", "response_format": "verbose_json"}
    if language:
        data["language"] = language

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, files=files, data=data)
        resp.raise_for_status()
        return resp.json()


async def transcribe_bytes(blob: bytes, suffix: str = ".wav") -> dict:
    """Convenience: transcribe raw bytes by writing to a temp file."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(blob)
        tmp_name = tmp.name
    tmp_path = Path(tmp_name)
    try:
        return await transcribe(tmp_path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass