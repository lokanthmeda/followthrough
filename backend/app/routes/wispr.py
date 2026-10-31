"""WhisperFlow routes (audio → transcript)."""
import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from ..services.whisper import transcribe_bytes

router = APIRouter(prefix="/wispr", tags=["WhisperFlow"])


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
    language: str | None = None,
):
    """Accept an audio file, forward it to the WhisperFlow proxy, return text.

    Accepts either ``file`` (proxy-style) or ``audio`` (UI-style) field names.
    """
    upload = file or audio
    if upload is None:
        raise HTTPException(status_code=400, detail="No audio file provided")
    if upload.content_type not in {"audio/wav", "audio/ogg", "audio/mpeg", "audio/webm",
                                   "application/octet-stream", "application/x-wav"}:
        raise HTTPException(status_code=415, detail="Unsupported audio type")

    blob = await upload.read()
    if len(blob) < 100:
        raise HTTPException(status_code=400, detail="Audio too short / empty")

    result = await transcribe_bytes(blob)
    return {
        "text": result.get("text", ""),
        "segments": result.get("segments", []),
        "language": result.get("language"),
        "model": "whisper-1",
    }