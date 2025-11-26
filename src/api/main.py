# ABOUTME: FastAPI application entry point for Marathon Trivia Platform.
# Configures routes, Temporal client, Redis connection, and middleware.

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import from_url
from temporalio.client import Client

from src.api.routes import player


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Lifespan context manager for FastAPI application.

    Handles startup and shutdown of external connections:
    - Temporal client connection
    - Redis connection

    Args:
        app: FastAPI application instance

    Yields:
        None (app runs with connections active)
    """
    # Startup: Connect to Temporal
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")

    app.state.temporal_client = await Client.connect(
        temporal_address,
        namespace=temporal_namespace,
    )

    # Startup: Connect to Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    app.state.redis = from_url(redis_url, decode_responses=True)  # type: ignore[no-untyped-call]

    yield

    # Shutdown: Close connections
    await app.state.redis.aclose()
    # Note: Temporal client doesn't need explicit close in current SDK


# Create FastAPI application
app = FastAPI(
    title="Marathon Trivia Platform",
    description="Multi-day trivia platform for trade show engagement",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(player.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with status "ok" to indicate service is running
    """
    return {"status": "ok"}
