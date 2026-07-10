import re

from better_profanity import profanity

from app.guardrails.base import GuardrailResult

_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# The agent must never invent a refund/credit amount that wasn't confirmed by a tool call.
_UNGROUNDED_MONEY_RE = re.compile(r"\$\s?\d+(\.\d{2})?")

_COMPETITOR_NAMES = {"ubereats", "uber eats", "doordash", "grubhub", "postmates"}

_BANNED_PHRASES = {
    "i guarantee",  # avoid over-promising outcomes support can't ensure
    "i promise",
}


def run_output_guardrails(
    text: str, *, grounded_amounts: set[str] | None = None
) -> GuardrailResult:
    """
    Validate the LLM's draft reply before it is spoken/sent to the user.

    grounded_amounts: dollar strings (e.g. "$12.50") that were actually returned by a
    backend tool call (order/refund service) during this turn — anything else that
    looks like a monetary promise is treated as an ungrounded hallucination risk.
    """
    flags: list[str] = []
    cleaned = text

    # 1. PII leak check — the agent should never surface stored card/SSN data back to the user
    if _CARD_RE.search(cleaned) or _SSN_RE.search(cleaned):
        cleaned = _CARD_RE.sub("[REDACTED]", cleaned)
        cleaned = _SSN_RE.sub("[REDACTED]", cleaned)
        flags.append("output_pii_redacted")

    # 2. Toxicity / profanity in generated content
    if profanity.contains_profanity(cleaned):
        return GuardrailResult(
            passed=False,
            cleaned_text=cleaned,
            flags=[*flags, "toxic_output_blocked"],
            blocked_reason="Generated reply failed the toxicity check and was blocked.",
        )

    # 3. Brand safety — don't let the agent recommend/mention competitor platforms
    lowered = cleaned.lower()
    if any(name in lowered for name in _COMPETITOR_NAMES):
        flags.append("competitor_mention_flagged")

    # 4. Over-promising language
    if any(phrase in lowered for phrase in _BANNED_PHRASES):
        flags.append("overpromise_language_flagged")

    # 5. Grounding check — flag dollar amounts not confirmed by a backend tool call
    grounded_amounts = grounded_amounts or set()
    for match in _UNGROUNDED_MONEY_RE.finditer(cleaned):
        amount_str = match.group(0)
        if amount_str not in grounded_amounts:
            flags.append(f"ungrounded_amount:{amount_str}")

    return GuardrailResult(passed=True, cleaned_text=cleaned, flags=flags)
