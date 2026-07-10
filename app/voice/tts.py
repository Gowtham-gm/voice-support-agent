from abc import ABC, abstractmethod

from openai import OpenAI

from app.core.config import settings


class BaseTTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Return synthesized audio bytes (mp3) for the given text."""


class OpenAITTS(BaseTTSProvider):
    """Wraps OpenAI's TTS endpoint. Swap for ElevenLabs/PlayHT/Azure by implementing
    the same interface."""

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def synthesize(self, text: str) -> bytes:
        response = self._client.audio.speech.create(
            model=settings.TTS_MODEL,
            voice=settings.TTS_VOICE,
            input=text,
        )
        return response.read()


def get_tts_provider() -> BaseTTSProvider:
    return OpenAITTS()
