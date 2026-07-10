from dataclasses import dataclass, field


@dataclass
class GuardrailResult:
    """Outcome of running a set of guardrail checks over a piece of text."""

    passed: bool
    cleaned_text: str
    flags: list[str] = field(default_factory=list)
    blocked_reason: str | None = None

    def merge(self, other: "GuardrailResult") -> "GuardrailResult":
        return GuardrailResult(
            passed=self.passed and other.passed,
            cleaned_text=other.cleaned_text,
            flags=[*self.flags, *other.flags],
            blocked_reason=self.blocked_reason or other.blocked_reason,
        )
