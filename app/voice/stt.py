from abc import ABC, abstractmethod
from io import BytesIO

from openai import OpenAI

from app.core.config import settings


class BaseSTTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """Return the transcript text for the given audio bytes."""


class OpenAIWhisperSTT(BaseSTTProvider):
    """Wraps OpenAI's Whisper transcription endpoint. Swap this class for
    Deepgram/AssemblyAI/Azure Speech by implementing the same interface."""

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        buffer = BytesIO(audio_bytes)
        buffer.name = filename  # OpenAI SDK infers format from the filename extension
        response = self._client.audio.transcriptions.create(
            model=settings.STT_MODEL,
            file=buffer,
        )
        return response.text.strip()


def get_stt_provider() -> BaseSTTProvider:
    return OpenAIWhisperSTT()
