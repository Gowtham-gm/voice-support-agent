import base64

from fastapi import UploadFile

from app.exceptions import AppException
from app.schemas.voice import ALLOWED_AUDIO_CONTENT_TYPES, MAX_AUDIO_BYTES


async def validate_and_read_audio(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_AUDIO_CONTENT_TYPES:
        raise AppException(
            f"Unsupported audio type '{file.content_type}'. "
            f"Allowed: {sorted(ALLOWED_AUDIO_CONTENT_TYPES)}",
            status_code=415,
        )

    data = await file.read()
    if len(data) == 0:
        raise AppException("Uploaded audio file is empty.", status_code=422)
    if len(data) > MAX_AUDIO_BYTES:
        raise AppException(
            f"Audio file too large. Max {MAX_AUDIO_BYTES // (1024 * 1024)}MB.",
            status_code=413,
        )
    return data


def audio_bytes_to_base64(audio_bytes: bytes) -> str:
    return base64.b64encode(audio_bytes).decode("utf-8")
