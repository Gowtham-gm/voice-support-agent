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

## Production Azure Architecture at Scale

This section documents the **target architecture** for running this system in production
on Azure at scale (hundreds–thousands of concurrent voice sessions). It is a design
reference, not a description of what's currently provisioned — `infra/main.bicep` and
`.github/workflows/deploy-azure.yml` cover a single-region starter deployment
(Container Apps + ACR). Treat everything below as the roadmap for evolving that starter
into the architecture described here.

### High-level topology

```
                                    Internet
                                        │
                              ┌─────────▼─────────┐
                              │   Azure Front Door │  (global anycast entry, WAF, TLS)
                              │   + WAF Policy     │
                              └─────────┬─────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 │                      │                      │
        Region: East US          Region: West Europe    Region: SE Asia (optional)
                 │                      │                      │
        ┌────────▼────────┐   ┌─────────▼────────┐   ┌─────────▼────────┐
        │  VNet (hub-spoke)│   │  VNet (hub-spoke) │   │  VNet (hub-spoke) │
        │                  │   │                   │   │                   │
        │ ┌──────────────┐ │   │ ┌──────────────┐  │   │ ┌──────────────┐  │
        │ │ App Gateway /  │   │ │ App Gateway /  │   │ │ App Gateway /  │
        │ │ Internal LB    │   │ │ Internal LB    │   │ │ Internal LB    │
        │ └──────┬───────┘ │   │ └──────┬───────┘  │   │ └──────┬───────┘  │
        │        ▼         │   │        ▼          │   │        ▼          │
        │ Container Apps    │   │ Container Apps     │   │ Container Apps     │
        │ Env (private,     │   │ Env (private,       │   │ Env (private,       │
        │ VNet-integrated)  │   │ VNet-integrated)    │   │ VNet-integrated)    │
        │  - API replicas   │   │  - API replicas     │   │  - API replicas     │
        │  - autoscale 3-40 │   │  - autoscale 3-40   │   │  - autoscale 3-40   │
        │                  │   │                   │   │                   │
        │ Private Endpoints:│   │ Private Endpoints: │   │ Private Endpoints: │
        │  - Postgres        │   │  - Postgres (read    │   │  - Postgres (read    │
        │    (primary)       │   │    replica)          │   │    replica)          │
        │  - Redis            │   │  - Redis (geo-repl)  │   │  - Redis (geo-repl)  │
        │  - Key Vault         │   │  - Key Vault          │   │  - Key Vault          │
        │  - ACR                │   │  - ACR                 │   │  - ACR                 │
        └──────────────────┘   └───────────────────┘   └───────────────────┘
                 │                      │                      │
                 └──────────────────────┴──────────────────────┘
                                        │
                      Azure OpenAI (regional, PTU-backed) +
                      Cartesia (external API, called over
                      internet egress with NAT Gateway)
```

### Networking

- **Hub-and-spoke VNet design**: a central hub VNet holds shared services (Azure
  Firewall, VPN/ExpressRoute gateway, DNS resolver); each region/environment is a spoke
  VNet peered to the hub. Keeps egress control, DNS, and security policy centralized
  rather than duplicated per environment.
- **Container Apps Environment runs VNet-integrated** (internal or external, depending
  on whether Front Door is the sole public entry point) so the API's outbound traffic to
  Postgres/Redis/Key Vault never leaves the private network.
- **Private Endpoints** for every stateful dependency — Azure Database for PostgreSQL,
  Azure Cache for Redis, Key Vault, and Container Registry — so none of them have a
  public IP or DNS name resolvable outside the VNet. Private DNS zones handle name
  resolution inside the VNet.
- **NAT Gateway** on the outbound path for calls to external APIs (OpenAI, Cartesia,
  any third-party webhook) — gives a small set of stable, allow-listable outbound IPs
  instead of unpredictable Container Apps platform IPs, which matters if a provider
  wants IP allow-listing on their side.
- **Azure Front Door** as the single global entry point: anycast routing to the nearest
  healthy region, TLS termination, and built-in DDoS protection (Front Door sits on
  Azure's global edge network). Regional failover is automatic — if a region's health
  probe fails, Front Door routes new traffic to the next-nearest healthy region.
- **DNS**: Azure DNS for public zones, Private DNS Zones linked to each spoke VNet for
  internal name resolution of private-endpoint-backed resources.

### Load balancing

- **Global tier — Azure Front Door**: distributes traffic across regions based on
  latency and health, terminates TLS, and applies the WAF policy before traffic ever
  reaches a region.
- **Regional tier — Container Apps' built-in ingress load balancer**: within a region,
  Container Apps distributes requests across replicas automatically as part of the
  platform; no separate load balancer resource is needed unless you introduce an
  Application Gateway for regional WAF/routing rules beyond what Front Door provides.
- **Scale-out trigger**: HTTP concurrency-based autoscaling (KEDA under the hood) — scale
  out when concurrent requests per replica crosses a threshold, not just on CPU. This
  matters here specifically because voice turns are I/O-bound (waiting on STT/LLM/TTS
  providers), so CPU stays low even when the app is saturated on in-flight requests —
  CPU-based scaling alone would under-scale this workload.
- **Session affinity is intentionally NOT used** at the load-balancer level — conversation
  state lives in Redis (see Notes on Production Hardening above), not in-process, so any
  replica in any region can serve any turn of any session. This is what makes multi-region
  active-active possible instead of falling back to regional pinning per user.
- **Database read scaling**: Postgres read replicas per region for read-heavy queries
  (order lookups, history), with writes routed to the primary region. Redis uses
  geo-replication (active-passive or active-active depending on consistency needs) to
  keep session state available close to wherever a request lands.

### Security

- **Identity**: Managed Identity (system- or user-assigned) on the Container App —
  no credentials in environment variables. The app authenticates to Key Vault, ACR,
  Postgres, and Redis via Azure AD tokens issued to the managed identity, not
  connection-string passwords.
- **Secrets**: all secrets (`JWT_SECRET`, `OPENAI_API_KEY`, `CARTESIA_API_KEY`,
  DB connection strings) live in Key Vault, referenced by Container Apps via
  Key Vault secret references — not as plain Container Apps secrets, which is what
  the starter `infra/main.bicep` uses for simplicity.
- **Network security**: Network Security Groups (NSGs) on every subnet restricting
  traffic to only the required ports/protocols between tiers; Azure Firewall in the hub
  VNet for centralized egress filtering and threat intelligence-based blocking.
- **WAF**: Front Door's WAF policy in front of every region, with OWASP core rule set
  plus custom rules tuned for this API's traffic shape (rate limiting per IP, blocking
  known bad user agents, geo-filtering if the app is region-restricted).
- **DDoS protection**: Azure DDoS Protection Standard on the VNets, layered under
  Front Door's edge-level mitigation.
- **Application-layer auth**: unchanged from what's already in the app — JWT access/
  refresh tokens and RBAC (`app/core/security.py`, `app/auth/rbac.py`) — but in
  production, consider moving JWT issuance/validation to Azure AD B2C or Entra External
  ID rather than hand-rolled JWTs, for built-in MFA, social login, and token revocation
  support at scale.
- **Data protection**: encryption at rest (default for Postgres/Redis/Storage),
  encryption in transit enforced (TLS-only connections to Postgres and Redis), and
  Microsoft Defender for Cloud enabled across the resource group for continuous
  posture assessment and threat detection.
- **Audit/compliance logging**: every guardrail trigger, auth event, and tool call
  (refund issuance, escalation) shipped to a centralized Log Analytics workspace with a
  retention policy matching compliance requirements — this is what makes the guardrail
  flags in `app/guardrails/` actually auditable rather than just in-request signals.

### Streaming (real-time voice)

The current pipeline (`app/voice/pipeline.py`) is a **cascading batch** design: full
audio in, full transcript, full LLM reply, full audio out — one request/response cycle
per turn. That's the right starting point, but it does not deliver the low end-to-end
latency that Cartesia's streaming-capable models (Ink-Whisper streaming STT, Sonic
WebSocket TTS) are actually built for. At scale, the architecture below is the
target for a true streaming voice experience:

- **Transport**: replace the single-shot `POST /api/v1/voice/session` with a
  **WebSocket** connection (FastAPI supports this natively) or **Azure Web PubSub**
  for managing large numbers of concurrent bidirectional connections without the API
  tier itself holding every socket — Web PubSub offloads connection management so
  Container Apps replicas only handle message processing, not long-lived socket state,
  which changes the scaling math significantly (socket count stops being coupled to
  replica count).
- **STT leg**: stream audio chunks to Cartesia's streaming STT (`ink-2`/`ink-whisper`
  over WebSocket) as the user speaks, instead of waiting for the full recording —
  partial transcripts arrive continuously.
- **LLM leg**: stream partial transcript fragments into the LangChain agent as they
  stabilize (turn-detection signals when the user has finished a thought), and stream
  the LLM's token-by-token output rather than waiting for the full completion.
- **TTS leg**: feed LLM output tokens into Cartesia's TTS WebSocket **as they're
  generated**, using a shared `context_id` so the audio stream is continuous rather
  than one request per sentence — this is what actually delivers Cartesia's sub-90ms
  latency figures end-to-end, versus the current batch pipeline which pays full
  round-trip latency at each of the three stages sequentially.
- **Guardrails on a stream**: input/output guardrails need to run on stabilized chunks
  (e.g. per completed sentence) rather than only once at the end — otherwise a
  streaming pipeline either loses the safety checks entirely or reintroduces the same
  end-to-end latency it was built to avoid. This is the main design challenge in moving
  from batch to streaming and needs explicit handling in `app/guardrails/`.
- **Connection scaling**: Azure Web PubSub scales to very large numbers of concurrent
  connections independent of the compute tier; Container Apps replicas remain
  stateless request/event processors behind it, consistent with the "no session
  affinity" principle above.
- **Regional pinning for streaming**: unlike the stateless HTTP case, an in-progress
  streaming voice session is latency-sensitive to which region it's connected to —
  Front Door's session affinity (opt-in, unlike the stateless HTTP tier) or Web PubSub's
  own regional routing should keep a single voice session pinned to one region for its
  duration, while still allowing the next session from the same user to land wherever is
  nearest.

### Scaling summary

| Layer | Mechanism |
|---|---|
| Global routing | Azure Front Door (anycast, health-based failover) |
| Regional load balancing | Container Apps built-in ingress LB (KEDA-driven autoscale) |
| Compute scale-out | HTTP concurrency-based autoscaling, 3–40+ replicas per region |
| Session/state | Azure Cache for Redis (geo-replicated), never in-process |
| Database | Azure Database for PostgreSQL Flexible Server, primary + regional read replicas |
| Real-time connections | Azure Web PubSub (decouples socket count from compute replicas) |
| External LLM/voice capacity | Azure OpenAI PTUs for predictable throughput; Cartesia via NAT-gated egress |
| Security perimeter | Front Door WAF → NSGs → Azure Firewall → Private Endpoints (defense in depth) |
| Identity | Managed Identity + Key Vault (no credentials in app config) |
| Observability | Log Analytics + Application Insights across all regions, centralized |


