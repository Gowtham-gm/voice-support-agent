from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    order_id: str | None = Field(default=None, max_length=50)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[str] = Field(default_factory=list)
    guardrail_flags: list[str] = Field(default_factory=list)
