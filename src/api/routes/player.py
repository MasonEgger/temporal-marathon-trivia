# ABOUTME: Player management API routes.
# Handles player registration and state queries.

import json

from fastapi import APIRouter, Cookie, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from temporalio.exceptions import ApplicationError

from src.api.routes.leaderboard import aggregate_leaderboards
from src.models.answer import EventStatusResponse, RegisterPlayerRequest
from src.workflows.daily import DailyWorkflow
from src.workflows.event import EventWorkflow
from src.workflows.player import PlayerEntityWorkflow

# Configure Jinja2 templates
templates = Jinja2Templates(directory="frontend/templates")

router = APIRouter()


@router.post("/api/join")
async def join(
    first_name: str = Form(),
    last_name: str = Form(),
    email: str = Form(),
) -> Response:
    """Register a new player and return HTML success fragment.

    Args:
        first_name: Player's first name from form
        last_name: Player's last name from form
        email: Player's email address from form

    Returns:
        HTMLResponse with success message and player_id cookie set,
        or error HTML fragment if validation fails

    Raises:
        No exceptions - all errors returned as HTML fragments
    """
    from src.api.main import app

    try:
        # Get Temporal client from app state
        temporal_client = app.state.temporal_client

        # Get EventWorkflow handle (assumes workflow is already running)
        # TODO: Get event_id from config or environment
        event_id = "default-event"
        handle = temporal_client.get_workflow_handle(event_id)

        # Call register_player update handler
        request = RegisterPlayerRequest(
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        player_id = await handle.execute_update(
            EventWorkflow.register_player,
            request,
        )

        # Render success template
        response = templates.TemplateResponse(
            name="components/join-success.html",
            context={"request": {}, "player_id": player_id},
        )

        # Set player_id cookie
        response.set_cookie(key="player_id", value=player_id)

        return response

    except ApplicationError as e:
        # Validation error from workflow (email, work domain, etc.)
        error_message = str(e)
        return templates.TemplateResponse(
            name="components/error.html",
            context={"request": {}, "error": error_message},
        )
    except Exception as e:
        # Unexpected error
        return templates.TemplateResponse(
            name="components/error.html",
            context={"request": {}, "error": f"An error occurred: {e}"},
        )


@router.get("/api/player", response_class=HTMLResponse)
async def get_player(
    request: Request,
    player_id: str | None = Cookie(None),
) -> HTMLResponse:
    """Get player's rank highlighted in leaderboard HTML.

    This endpoint:
    1. Validates player_id cookie
    2. Queries PlayerEntityWorkflow to get player's email
    3. Fetches full leaderboard (with aggregation)
    4. Renders leaderboard with player's row highlighted

    Args:
        request: FastAPI request object
        player_id: Player ID from cookie (optional for manual validation)

    Returns:
        HTMLResponse: Leaderboard HTML with player's row highlighted,
        or error HTML if validation fails
    """
    # Manual cookie validation for HTMX pattern
    if not player_id:
        return templates.TemplateResponse(
            name="components/error.html",
            context={"request": request, "error": "Please register first"},
        )

    try:
        temporal_client = request.app.state.temporal_client
        redis = request.app.state.redis

        # Get player's email from PlayerEntityWorkflow
        player_handle = temporal_client.get_workflow_handle(player_id)
        player_state = await player_handle.query(PlayerEntityWorkflow.get_current_state)
        player_email = player_state.player.email

        # Check Redis cache for leaderboard
        cache_key = "leaderboard:full"
        cached_data = await redis.get(cache_key)

        if cached_data:
            # Use cached leaderboard
            from src.models.leaderboard import LeaderboardEntry

            leaderboard_entries = [LeaderboardEntry(**entry) for entry in json.loads(cached_data)]
        else:
            # Cache miss - fetch and aggregate leaderboard
            import os

            event_id = os.getenv("EVENT_WORKFLOW_ID", "marathon-trivia-event")
            event_handle = temporal_client.get_workflow_handle(event_id)
            event_status: EventStatusResponse = await event_handle.query(
                EventWorkflow.get_event_status
            )

            # Query each DailyWorkflow
            daily_leaderboards = []
            for daily_workflow_id in event_status.daily_workflow_ids.values():
                daily_handle = temporal_client.get_workflow_handle(daily_workflow_id)
                daily_leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)
                daily_leaderboards.append(daily_leaderboard)

            # Aggregate
            leaderboard_entries = aggregate_leaderboards(daily_leaderboards)

            # Cache for future requests
            serialized = json.dumps([entry.__dict__ for entry in leaderboard_entries])
            await redis.set(cache_key, serialized, ex=30)

        # Find player's entry
        player_entry = next(
            (entry for entry in leaderboard_entries if entry.email == player_email),
            None,
        )

        # Get event dates for column headers
        config = request.app.state.config
        event_dates = [d.isoformat() for d in config.get_all_dates()]

        # Render leaderboard with highlight
        return templates.TemplateResponse(
            name="components/leaderboard.html",
            context={
                "request": request,
                "leaderboard": leaderboard_entries,
                "event_dates": event_dates,
                "highlight_email": player_email if player_entry else None,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            name="components/error.html",
            context={"request": request, "error": f"Error loading leaderboard: {e}"},
        )
