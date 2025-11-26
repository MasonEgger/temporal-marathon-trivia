# ABOUTME: Gameplay API routes for answering questions.
# Handles starting days, submitting answers, and returning questions.


from fastapi import APIRouter, Cookie, Form, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from temporalio.client import Client
from temporalio.exceptions import ApplicationError

from src.models.answer import SubmitAnswerRequest
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
                request,
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
            request,
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
            request,
            name="components/error.html",
            context={"error": str(e)},
        )
    except Exception as e:
        # Unexpected errors (network issues, etc.)
        return templates.TemplateResponse(
            request,
            name="components/error.html",
            context={"error": f"An error occurred: {e}"},
        )


@router.post("/api/day/{date}/answer", response_class=HTMLResponse)
async def submit_answer(
    request: Request,
    date: str = Path(..., description="Date in YYYY-MM-DD format"),
    question_id: str = Form(..., description="ID of the question being answered"),
    answer_choice: str = Form(..., description="Player's answer choice (A/B/C/D)"),
    player_id: str | None = Cookie(None),
) -> HTMLResponse:
    """Submit an answer to a trivia question.

    This endpoint accepts a player's answer submission and orchestrates the workflow
    to validate the answer, update scores, and return either the next question or
    a completion message.

    Args:
        request: FastAPI request object (required for templates)
        date: The date string in YYYY-MM-DD format
        question_id: The ID of the question being answered
        answer_choice: The player's answer choice (A, B, C, or D)
        player_id: Player ID from cookie (optional, validated manually for HTMX compatibility)

    Returns:
        HTMLResponse: HTML fragment with next question, completion message, or error

    Note:
        All errors return 200 + error HTML (not HTTP error codes) to maintain
        HTMX compatibility. Response routing depends on AnswerResult:
        - next_question exists → render question.html
        - completion_message exists → render completion.html
    """
    try:
        # Validate player_id cookie is present (OUR application logic)
        if not player_id:
            return templates.TemplateResponse(
                request,
                name="components/error.html",
                context={
                    "request": request,
                    "error": "Please register first to submit answers",
                },
            )

        # Get Temporal client and config from app state
        client: Client = request.app.state.temporal_client
        config = request.app.state.config

        # Get PlayerEntityWorkflow handle using player_id from cookie
        handle = client.get_workflow_handle(
            workflow_id=player_id,
            run_id=None,
        )

        # Call submit_answer update handler with type-safe request model
        answer_result = await handle.execute_update(
            PlayerEntityWorkflow.submit_answer,
            SubmitAnswerRequest(
                date=date,
                question_id=question_id,
                answer_choice=answer_choice,
                show_correct_answer=config.show_correct_answer,
            ),
        )

        # Route response based on AnswerResult (OUR application logic)
        if answer_result.next_question:
            # More questions remain - render next question
            return templates.TemplateResponse(
                request,
                name="components/question.html",
                context={
                    "request": request,
                    "question": answer_result.next_question,
                    "date": date,
                    "question_number": answer_result.current_score + 1,
                    "is_correct": answer_result.is_correct,
                    "correct_answer": answer_result.correct_answer,
                },
            )
        else:
            # All questions answered - render completion
            return templates.TemplateResponse(
                request,
                name="components/completion.html",
                context={
                    "request": request,
                    "completion_message": answer_result.completion_message,
                    "score": answer_result.current_score,
                    "total": answer_result.total_questions,
                    "date": date,
                },
            )

    except ApplicationError as e:
        # Workflow validation errors (invalid answer_choice, etc.)
        return templates.TemplateResponse(
            request,
            name="components/error.html",
            context={"error": str(e)},
        )
    except Exception as e:
        # Unexpected errors (network issues, etc.)
        return templates.TemplateResponse(
            request,
            name="components/error.html",
            context={"error": f"An error occurred: {e}"},
        )
