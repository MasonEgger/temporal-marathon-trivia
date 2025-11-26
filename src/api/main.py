# ABOUTME: FastAPI application entry point for Marathon Trivia Platform.
# Configures routes, Temporal client, Redis connection, and middleware.

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from redis.asyncio import from_url

from src.activities.config import ConfigActivities
from src.api.routes import gameplay, leaderboard, player
from src.temporal_client import create_temporal_client

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Lifespan context manager for FastAPI application.

    Handles startup and shutdown of external connections:
    - Load EventConfig and UXConfig from TOML file
    - Temporal client connection
    - Redis connection

    Args:
        app: FastAPI application instance

    Yields:
        None (app runs with connections active)
    """
    # Startup: Load EventConfig and UXConfig from TOML file
    config_path = os.getenv("EVENT_CONFIG_PATH", "config/event.toml")
    config_activities = ConfigActivities()
    app.state.config = config_activities.load_event_config(config_path)
    app.state.ux_config = config_activities.load_ux_config(config_path)

    # Startup: Connect to Temporal (supports both local and cloud)
    app.state.temporal_client = await create_temporal_client()

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

# Configure Jinja2 templates
templates = Jinja2Templates(directory="frontend/templates")

# Include routers
app.include_router(player.router)
app.include_router(gameplay.router)
app.include_router(leaderboard.router)


@app.get("/", response_class=HTMLResponse)
async def landing_page(
    request: Request,
    player_id: str | None = Cookie(None),
) -> HTMLResponse:
    """Landing page for Marathon Trivia Platform.

    Renders different views based on player registration status:
    - First-time visitors (no cookie): Show registration form
    - Returning players (has cookie): Show day buttons and leaderboard

    Args:
        request: FastAPI request object for template context
        player_id: Optional player_id from cookie (None for first-time visitors)

    Returns:
        HTMLResponse with rendered landing.html template
    """
    # Get configuration from app state
    config = request.app.state.ux_config
    event_config = request.app.state.config

    # Build template context
    context = {
        "request": request,
        "config": config,
        "player_id": player_id,
    }

    # If returning player, add event dates and player-specific data
    if player_id:
        # Get all event dates
        event_dates = event_config.get_all_dates()
        context["event_dates"] = event_dates
        context["current_date"] = date.today()

        # Get player's completed days
        try:
            from src.workflows.player import PlayerEntityWorkflow

            workflow_id = player_id
            handle = request.app.state.temporal_client.get_workflow_handle(workflow_id)
            player_state = await handle.query(PlayerEntityWorkflow.get_current_state)
            context["player_completed_days"] = player_state.player.completed_days
        except Exception:
            # If we can't get player state, show empty completed days
            context["player_completed_days"] = set()

    return templates.TemplateResponse(request, "landing.html", context)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with status "ok" to indicate service is running
    """
    return {"status": "ok"}
