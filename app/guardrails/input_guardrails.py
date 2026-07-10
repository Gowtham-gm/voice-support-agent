import re

from better_profanity import profanity

from app.core.config import settings
from app.guardrails.base import GuardrailResult

profanity.load_censor_words()

# --- Prompt injection heuristics ---
_INJECTION_PATTERNS = [
    r"ignore (all|any|previous|the above|prior) instructions",
    r"disregard (all|any|previous|the above|prior) (instructions|rules)",
    r"you are now",
    r"act as (a|an) (?!customer)",
    r"system prompt",
    r"reveal (your|the) (prompt|instructions|system message)",
    r"pretend (you are|to be)",
    r"jailbreak",
    r"do anything now",
    r"\bDAN\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# --- Basic PII patterns (card numbers, emails, phone, SSN-like) ---
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Keywords that keep the conversation within the food-delivery support domain.
_IN_SCOPE_KEYWORDS = {
    "order", "delivery", "refund", "menu", "restaurant", "driver", "courier",
    "payment", "charge", "cancel", "late", "missing", "wrong", "cold", "coupon",
    "discount", "account", "app", "tip", "rider", "eta", "track", "address",
    "hello", "hi", "help", "support", "thanks", "thank", "issue", "problem",
    "food", "item", "restaurant", "receipt", "invoice", "subscription",
}


def _redact_pii(text: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    redacted = text
    for pattern, label in (
        (_CARD_RE, "card_number"),
        (_SSN_RE, "ssn"),
        (_EMAIL_RE, "email"),
        (_PHONE_RE, "phone"),
    ):
        if pattern.search(redacted):
            flags.append(f"pii_redacted:{label}")
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, flags


def _check_scope(text: str) -> bool:
    """Loose heuristic: flag only if message is long AND shares no domain keywords."""
    lowered = text.lower()
    if len(text.split()) < 4:
        return True  # short messages (greetings etc.) always allowed through
    return any(kw in lowered for kw in _IN_SCOPE_KEYWORDS)


def run_input_guardrails(text: str) -> GuardrailResult:
    flags: list[str] = []

    # 1. Length check
    if len(text) > settings.MAX_INPUT_CHARS:
        return GuardrailResult(
            passed=False,
            cleaned_text=text,
            flags=["input_too_long"],
            blocked_reason=f"Message exceeds {settings.MAX_INPUT_CHARS} characters.",
        )

    # 2. Prompt injection detection
    if _INJECTION_RE.search(text):
        return GuardrailResult(
            passed=False,
            cleaned_text=text,
            flags=["prompt_injection_suspected"],
            blocked_reason="Message appears to attempt to override system instructions.",
        )

    # 3. Profanity / abuse
    if profanity.contains_profanity(text):
        flags.append("profanity_detected")
        text = profanity.censor(text)

    # 4. PII redaction (never send raw PII into the LLM context)
    if settings.ENABLE_PII_REDACTION:
        text, pii_flags = _redact_pii(text)
        flags.extend(pii_flags)

    # 5. Topic/scope check (soft — flags but does not block, avoids false blocks)
    if not _check_scope(text):
        flags.append("possibly_off_topic")

    return GuardrailResult(passed=True, cleaned_text=text, flags=flags)
