from dataclasses import dataclass, field

from app.core.logging import logger
from app.exceptions import GuardrailViolationError
from app.guardrails.input_guardrails import run_input_guardrails
from app.guardrails.output_guardrails import run_output_guardrails
from app.llm.orchestrator import run_agent_turn
from app.utils.audio import audio_bytes_to_base64
from app.voice.stt import get_stt_provider
from app.voice.tts import get_tts_provider


@dataclass
class VoiceTurnResult:
    transcript: str
    reply_text: str
    audio_base64: str
    guardrail_flags: list[str] = field(default_factory=list)


def run_voice_turn(session_id: str, audio_bytes: bytes, filename: str) -> VoiceTurnResult:
    flags: list[str] = []

    # 1. Speech-to-Text
    stt = get_stt_provider()
    transcript = stt.transcribe(audio_bytes, filename)
    logger.info("session=%s stt_transcript=%r", session_id, transcript)

    if not transcript.strip():
        raise GuardrailViolationError("Could not detect any speech in the audio.")

    # 2. Input guardrails
    input_result = run_input_guardrails(transcript)
    flags.extend(input_result.flags)
    if not input_result.passed:
        raise GuardrailViolationError(
            input_result.blocked_reason or "Input blocked by guardrails.",
            violations=input_result.flags,
        )

    # 3. LangChain agent orchestration (tool-calling, grounded in backend data)
    agent_result = run_agent_turn(session_id, input_result.cleaned_text)

    # 4. Output guardrails
    output_result = run_output_guardrails(
        agent_result.reply, grounded_amounts=agent_result.grounded_amounts
    )
    flags.extend(output_result.flags)
    if not output_result.passed:
        raise GuardrailViolationError(
            output_result.blocked_reason or "Generated reply blocked by guardrails.",
            violations=output_result.flags,
        )

    # 5. Text-to-Speech
    tts = get_tts_provider()
    audio_out = tts.synthesize(output_result.cleaned_text)

    return VoiceTurnResult(
        transcript=transcript,
        reply_text=output_result.cleaned_text,
        audio_base64=audio_bytes_to_base64(audio_out),
        guardrail_flags=flags,
    )
