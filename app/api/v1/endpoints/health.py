from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@router.get("/ready")
def ready() -> dict:
    # Extend with real checks: DB ping, OpenAI key presence, etc.
    checks = {"openai_key_configured": bool(settings.OPENAI_API_KEY)}
    return {"status": "ready" if all(checks.values()) else "degraded", "checks": checks}
