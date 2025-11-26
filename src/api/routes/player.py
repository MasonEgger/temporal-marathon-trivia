# ABOUTME: Player management API routes.
# Handles player registration and state queries.

import json
import os

from fastapi import APIRouter, Cookie, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from temporalio.exceptions import ApplicationError

from src.api.player_verification import verify_player_workflow
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
    request: Request,
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
        event_id = os.getenv("EVENT_WORKFLOW_ID", "default-event")
        handle = temporal_client.get_workflow_handle(event_id)

        # Call register_player update handler
        register_request = RegisterPlayerRequest(
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        player_id = await handle.execute_update(
            EventWorkflow.register_player,
            register_request,
        )

        # Redirect to home page (which will show game interface now that user is registered)
        response = RedirectResponse(url="/", status_code=303)

        # Set player_id cookie
        response.set_cookie(key="player_id", value=player_id)

        return response

    except ApplicationError as e:
        # Validation error from workflow (email, work domain, etc.)
        error_message = str(e)
        return templates.TemplateResponse(request, "components/error.html", {"error": error_message})
    except Exception as e:
        # Unexpected error
        return templates.TemplateResponse(request, "components/error.html", {"error": f"An error occurred: {e}"})


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
        return templates.TemplateResponse(request, "components/error.html", {"error": "Please register first"})

    try:
        temporal_client = request.app.state.temporal_client
        redis = request.app.state.redis

        # Verify PlayerEntityWorkflow exists (handles server restarts gracefully)
        player_handle = await verify_player_workflow(player_id, temporal_client)
        if player_handle is None:
            # Workflow doesn't exist - clear cookie and show error
            response = templates.TemplateResponse(
                request,
                "components/error.html",
                {"error": "Session expired. Please register again."},
            )
            response.delete_cookie(key="player_id")
            return response

        # Get player's email from PlayerEntityWorkflow
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
            event_status: EventStatusResponse = await event_handle.query(EventWorkflow.get_event_status)

            # Query each DailyWorkflow
            daily_leaderboards = []
            for date_str, daily_workflow_id in event_status.daily_workflow_ids.items():
                daily_handle = temporal_client.get_workflow_handle(daily_workflow_id)
                daily_leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)
                daily_leaderboards.append((date_str, daily_leaderboard))

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
            request,
            "components/leaderboard.html",
            {
                "leaderboard": leaderboard_entries,
                "event_dates": event_dates,
                "highlight_email": player_email if player_entry else None,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "components/error.html",
            {"error": f"Error loading leaderboard: {e}"},
        )
