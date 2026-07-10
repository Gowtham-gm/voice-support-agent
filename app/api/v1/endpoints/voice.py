from fastapi import APIRouter, Depends, Form, UploadFile

from app.core.dependencies import rate_limiter, require_permission
from app.db.models import User
from app.schemas.voice import VoiceResponse
from app.utils.audio import validate_and_read_audio
from app.voice.pipeline import run_voice_turn

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/session", response_model=VoiceResponse, dependencies=[Depends(rate_limiter)])
async def voice_session(
    session_id: str = Form(..., min_length=1, max_length=100),
    order_id: str | None = Form(default=None, max_length=50),
    audio: UploadFile = ...,
    current_user: User = Depends(require_permission("voice")),
) -> VoiceResponse:
    audio_bytes = await validate_and_read_audio(audio)

    result = run_voice_turn(
        session_id=session_id,
        audio_bytes=audio_bytes,
        filename=audio.filename or "input.wav",
    )

    return VoiceResponse(
        session_id=session_id,
        transcript=result.transcript,
        reply_text=result.reply_text,
        audio_base64=result.audio_base64,
        guardrail_flags=result.guardrail_flags,
    )
