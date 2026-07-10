from fastapi import APIRouter, Depends

from app.core.dependencies import rate_limiter, require_permission
from app.db.models import User
from app.exceptions import GuardrailViolationError
from app.guardrails.input_guardrails import run_input_guardrails
from app.guardrails.output_guardrails import run_output_guardrails
from app.llm.orchestrator import run_agent_turn
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limiter)])
def chat(
    payload: ChatRequest,
    current_user: User = Depends(require_permission("chat")),
) -> ChatResponse:
    flags: list[str] = []

    # Input guardrails
    input_result = run_input_guardrails(payload.message)
    flags.extend(input_result.flags)
    if not input_result.passed:
        raise GuardrailViolationError(
            input_result.blocked_reason or "Input blocked by guardrails.",
            violations=input_result.flags,
        )

    # LangChain agent orchestration
    agent_result = run_agent_turn(payload.session_id, input_result.cleaned_text)

    # Output guardrails
    output_result = run_output_guardrails(
        agent_result.reply, grounded_amounts=agent_result.grounded_amounts
    )
    flags.extend(output_result.flags)
    if not output_result.passed:
        raise GuardrailViolationError(
            output_result.blocked_reason or "Generated reply blocked by guardrails.",
            violations=output_result.flags,
        )

    return ChatResponse(
        session_id=payload.session_id,
        reply=output_result.cleaned_text,
        tool_calls=agent_result.tool_calls,
        guardrail_flags=flags,
    )
