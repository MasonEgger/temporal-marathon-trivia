# ABOUTME: Player management API routes.
# Handles player registration and state queries.

from fastapi import APIRouter, Form, Response
from fastapi.templating import Jinja2Templates
from temporalio.exceptions import ApplicationError

from src.models.answer import RegisterPlayerRequest
from src.workflows.event import EventWorkflow

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
