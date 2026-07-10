from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.db.session import init_db
from app.exceptions import AppException, app_exception_handler


def create_app() -> FastAPI:
    configure_logging(settings.DEBUG)

    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Cascading voice AI customer support agent for a food delivery app.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppException, app_exception_handler)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.on_event("startup")
    def _on_startup() -> None:
        init_db()
        logger.info("%s started (env=%s)", settings.APP_NAME, settings.ENV)

    return app


app = create_app()
