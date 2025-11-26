# ABOUTME: Gameplay API routes for answering questions.
# Handles starting days, submitting answers, and returning questions.


from fastapi import APIRouter, Cookie, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from temporalio.client import Client
from temporalio.exceptions import ApplicationError

from src.workflows.player import PlayerEntityWorkflow

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/api/day/{date}/start", response_class=HTMLResponse)
async def start_day(
    request: Request,
    date: str = Path(..., description="Date in YYYY-MM-DD format"),
    player_id: str | None = Cookie(None),
) -> HTMLResponse:
    """Start a day's trivia questions for a player.

    This endpoint initiates a day's gameplay by calling the PlayerEntityWorkflow's
    start_day update handler, which returns the first question.

    Args:
        request: FastAPI request object (required for templates)
        date: The date string in YYYY-MM-DD format
        player_id: Player ID from cookie (optional, validated manually for HTMX compatibility)

    Returns:
        HTMLResponse: HTML fragment with first question or error message

    Note:
        All errors return 200 + error HTML (not HTTP error codes) to maintain
        HTMX compatibility and enable seamless error display in the UI.
    """
    try:
        # Validate player_id cookie is present (OUR application logic)
        # We do this manually instead of Cookie(...) to return HTMX-friendly error HTML
        if not player_id:
            return templates.TemplateResponse(
                name="components/error.html",
                context={
                    "request": request,
                    "error": "Please register first to start playing",
                },
            )

        # Get Temporal client from app state
        client: Client = request.app.state.temporal_client

        # Get PlayerEntityWorkflow handle using player_id from cookie
        handle = client.get_workflow_handle(
            workflow_id=player_id,
            run_id=None,
        )

        # Call start_day update handler to get first question
        question = await handle.execute_update(
            PlayerEntityWorkflow.start_day,
            date,
        )

        # Render question template with question data
        return templates.TemplateResponse(
            name="components/question.html",
            context={
                "request": request,
                "question": question,
                "date": date,
                "question_number": 1,
                # Total questions not available yet - will be added later
            },
        )

    except ApplicationError as e:
        # Workflow validation errors (day not started, already completed, etc.)
        return templates.TemplateResponse(
            name="components/error.html",
            context={"request": request, "error": str(e)},
        )
    except Exception as e:
        # Unexpected errors (network issues, etc.)
        return templates.TemplateResponse(
            name="components/error.html",
            context={"request": request, "error": f"An error occurred: {e}"},
        )
