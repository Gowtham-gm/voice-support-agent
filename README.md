# Voice Support Agent — Food Delivery Customer Support

A modular, production-shaped backend for a **cascading voice AI customer support agent**
(STT → LLM/Orchestration → TTS) for a food delivery app, with FastAPI, JWT auth + RBAC,
LangChain-based orchestration/tools, and input/output guardrails.

## Architecture

```
                        ┌─────────────────────────────────────────────┐
                        │                 FastAPI App                  │
                        │  (auth, validation, rate limiting, routing)  │
                        └───────────────────┬───────────────────────────┘
                                             │
                 ┌───────────────────────────┼───────────────────────────┐
                 │                            │                           │
          /api/v1/auth               /api/v1/chat (text)         /api/v1/voice (audio)
                 │                            │                           │
                 ▼                            ▼                           ▼
         JWT issue/refresh          ┌──────────────────┐        ┌──────────────────────┐
         RBAC (customer/agent/      │  Input Guardrails │        │   Cascading Pipeline  │
         admin)                     │  (PII, injection, │        │  1. STT (audio→text)  │
                                     │  profanity, scope)│        │  2. Input Guardrails  │
                                     └─────────┬─────────┘        │  3. LangChain Agent   │
                                               ▼                  │  4. Output Guardrails │
                                     ┌──────────────────┐         │  5. TTS (text→audio)  │
                                     │ LangChain Agent/  │◄────────┘                       │
                                     │ Orchestrator      │        └──────────────────────┘
                                     │  - order lookup   │
                                     │  - refund tool     │
                                     │  - menu tool        │
                                     │  - escalate tool     │
                                     └─────────┬───────────┘
                                               ▼
                                     ┌──────────────────┐
                                     │ Output Guardrails │
                                     │ (PII leak, halluc.│
                                     │ toxicity, brand)  │
                                     └──────────────────┘
```

## Module Layout

```
app/
├── main.py                    # FastAPI app factory, middleware, exception handlers
├── core/
│   ├── config.py              # Settings (env-driven, pydantic-settings)
│   ├── security.py            # Password hashing, JWT encode/decode
│   ├── dependencies.py        # get_current_user, RBAC role guard, rate limiter
│   └── logging.py             # Structured logging config
├── api/v1/
│   ├── router.py              # Aggregates all v1 routers
│   └── endpoints/
│       ├── auth.py            # /register /login /refresh /me
│       ├── chat.py            # /chat  (text-based support)
│       ├── voice.py           # /voice/session (audio in -> audio out)
│       └── health.py          # /health /ready
├── schemas/                   # Pydantic request/response models (validation layer)
│   ├── auth.py
│   ├── chat.py
│   └── voice.py
├── db/
│   ├── session.py             # SQLAlchemy engine/session
│   └── models.py              # User ORM model
├── auth/
│   └── rbac.py                 # Roles + permission definitions
├── voice/
│   ├── stt.py                  # Speech-to-Text provider wrapper (Whisper API)
│   ├── tts.py                  # Text-to-Speech provider wrapper
│   └── pipeline.py             # Cascading STT->Guardrail->LLM->Guardrail->TTS orchestrator
├── llm/
│   ├── orchestrator.py         # LangChain agent construction
│   ├── prompts.py              # System / guardrail prompts
│   ├── tools.py                # LangChain Tools: order status, refund, menu, escalate
│   └── memory.py                # Per-session conversation memory store
├── guardrails/
│   ├── base.py                  # GuardrailResult, GuardrailViolation
│   ├── input_guardrails.py      # Prompt-injection, PII, profanity, scope checks
│   └── output_guardrails.py     # PII leak, toxicity, hallucination/grounding, brand tone
├── services/
│   ├── order_service.py         # Mock order data access (swap for real DB/API)
│   └── customer_service.py      # Mock customer data access
├── utils/
│   └── audio.py                  # Audio format helpers
└── exceptions.py                 # Custom exceptions + handlers
```

## Cascading Voice Pipeline

`POST /api/v1/voice/session` accepts an audio file + session id:

1. **STT** — `app/voice/stt.py` transcribes audio (OpenAI Whisper API by default;
   swap-in Deepgram/AssemblyAI/Azure by implementing `BaseSTTProvider`).
2. **Input Guardrails** — reject prompt injection, PII in unexpected fields, abusive
   language, off-scope requests (`app/guardrails/input_guardrails.py`).
3. **LangChain Orchestration** — an agent with tools (`order_status`, `refund_request`,
   `menu_lookup`, `escalate_to_human`) generates a grounded reply
   (`app/llm/orchestrator.py`).
4. **Output Guardrails** — block PII leakage, toxic/off-brand language, and
   ungrounded claims (e.g. inventing a refund amount) before it ever reaches TTS.
5. **TTS** — `app/voice/tts.py` synthesizes the guarded reply back to audio.

Every stage is provider-agnostic behind small interfaces, so you can swap
OpenAI/Whisper/ElevenLabs for Deepgram/Azure/PlayHT etc. without touching the pipeline.

## Auth & Authorization

- JWT access + refresh tokens (`app/core/security.py`).
- Password hashing via `passlib[bcrypt]`.
- Role-based access control (`customer`, `support_agent`, `admin`) enforced via
  a FastAPI dependency (`app/core/dependencies.py`, `app/auth/rbac.py`).
- Per-request Pydantic validation on every endpoint (`app/schemas/*`).

## Quickstart

```bash
cp .env.example .env          # fill in OPENAI_API_KEY, JWT_SECRET, etc.
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Or with Docker:

```bash
docker compose up --build
```

Docs: http://localhost:8000/docs

## Testing

```bash
pytest -v
```

## Notes on Production Hardening

- Swap SQLite for Postgres by changing `DATABASE_URL` (SQLAlchemy is already async-ready to extend).
- Add Redis-backed session/conversation memory for multi-instance deployments (`app/llm/memory.py` has a clear interface to swap the in-memory store).
- Put a real rate limiter (e.g. `slowapi` + Redis) behind `app/core/dependencies.py::rate_limiter`.
- Guardrails here are heuristic/regex + LLM-classifier based starting points — for
  regulated deployments, pair with a dedicated guardrails service (e.g. Guardrails AI,
  NeMo Guardrails, or a moderation API) and log all guardrail triggers for audit.
