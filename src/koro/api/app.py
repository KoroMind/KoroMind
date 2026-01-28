"""FastAPI application for KoroMind REST API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from koro.api.middleware import api_key_middleware, rate_limit_middleware
from koro.api.routes import health, messages, sessions, settings
from koro.core.config import (
    KOROMIND_CORS_ORIGINS,
    KOROMIND_HOST,
    KOROMIND_PORT,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("KoroMind API starting up...")
    yield
    logger.info("KoroMind API shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="KoroMind API",
        description="REST API for KoroMind - your personal AI assistant",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=KOROMIND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add API key authentication middleware
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(api_key_middleware)

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(messages.router, prefix="/api/v1", tags=["Messages"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])
    app.include_router(settings.router, prefix="/api/v1", tags=["Settings"])

    return app


# Create the default app instance
app = create_app()


def run_server():
    """Run the API server."""
    import uvicorn

    uvicorn.run(
        "koro.api.app:app",
        host=KOROMIND_HOST,
        port=KOROMIND_PORT,
        reload=False,
    )


if __name__ == "__main__":
    run_server()
