from pydantic import BaseModel, Field

ALLOWED_AUDIO_CONTENT_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/webm", "audio/x-m4a"}
MAX_AUDIO_BYTES = 15 * 1024 * 1024  # 15 MB


class VoiceSessionMeta(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    order_id: str | None = Field(default=None, max_length=50)


class VoiceResponse(BaseModel):
    session_id: str
    transcript: str
    reply_text: str
    audio_base64: str
    audio_content_type: str = "audio/mpeg"
    guardrail_flags: list[str] = Field(default_factory=list)
