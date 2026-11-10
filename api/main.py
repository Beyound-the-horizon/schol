"""Scholarship Platform FastAPI Application Entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.config import settings
from api.db import close_db_pool, init_db_pool
from api.routers.health import router as health_router
from api.routers.ingestion import router as ingestion_router
from api.routers.scholarships import router as scholarships_router
from api.routers.admin import router as admin_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info("Initializing application resources and database connection pool...")
    try:
        await init_db_pool()
    except Exception as exc:
        logger.warning(
            "Database pool initialization warning (will retry on incoming requests): %s",
            exc,
        )
    yield
    logger.info("Disposing application resources and closing database connection pool...")
    await close_db_pool()


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="Scholarship Platform API",
        version="1.0.0",
        description=(
            "Centralized backend service for scholarship discovery, public search, "
            "and authenticated crawler ingestion."
        ),
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    origins = (
        settings.cors_origins
        if isinstance(settings.cors_origins, list)
        else [settings.cors_origins]
    )
    logger.info("Configured CORS allowed origins: %s", origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )

    # Register Routers under /api/v1
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(scholarships_router, prefix=settings.api_prefix)
    app.include_router(ingestion_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)

    # Global unhandled exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled server exception at %s: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred. Please contact the platform team."
            },
        )

    return app


# Application singleton instance for ASGI servers (uvicorn api.main:app)
app = create_app()
