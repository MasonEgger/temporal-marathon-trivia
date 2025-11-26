# ABOUTME: Gameplay API routes for answering questions.
# Handles starting days, submitting answers, and returning questions.


from fastapi import APIRouter, Cookie, Form, Path, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from temporalio.client import Client
from temporalio.exceptions import ApplicationError

from src.api.player_verification import verify_player_workflow
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

        # Verify PlayerEntityWorkflow exists (handles server restarts gracefully)
        handle = await verify_player_workflow(player_id, client)
        if handle is None:
            # Workflow doesn't exist and couldn't be recreated - clear cookie and require re-registration
            response = templates.TemplateResponse(
                request,
                name="components/error.html",
                context={
                    "request": request,
                    "error": "Session expired. Please register again to continue playing.",
                },
            )
            response.delete_cookie(key="player_id")
            return response

        # Call start_day update handler to get current question (first if new, current if resuming)
        question = await handle.execute_update(
            PlayerEntityWorkflow.start_day,
            date,
        )

        # Get player state to determine actual question number (for resume functionality)
        player_state = await handle.query(PlayerEntityWorkflow.get_current_state)
        question_number = player_state.current_question_index + 1  # Convert 0-based to 1-based
        total_questions = len(player_state.current_questions) if player_state.current_questions else 0

        # Render question template with question data
        return templates.TemplateResponse(
            request,
            name="components/question.html",
            context={
                "request": request,
                "question": question,
                "date": date,
                "question_number": question_number,
                "total_questions": total_questions,
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

        # Verify PlayerEntityWorkflow exists (handles server restarts gracefully)
        handle = await verify_player_workflow(player_id, client)
        if handle is None:
            # Workflow doesn't exist - clear cookie and require re-registration
            response = templates.TemplateResponse(
                request,
                name="components/error.html",
                context={
                    "request": request,
                    "error": "Session expired. Please register again to continue playing.",
                },
            )
            response.delete_cookie(key="player_id")
            return response

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
            # More questions remain - render next question with feedback about previous
            # Get player state to find the question they just answered (for feedback display)
            player_state = await handle.query(PlayerEntityWorkflow.get_current_state)
            current_questions = player_state.current_questions or []

            # Find the answered question by ID and its position
            answered_question = None
            answered_question_index = None
            for i, q in enumerate(current_questions):
                if q.id == question_id:
                    answered_question = q
                    answered_question_index = i
                    break

            # If we found the answered question AND show_correct_answer is enabled, show feedback
            if answered_question and config.show_correct_answer:
                # Calculate question numbers (1-based)
                answered_question_number = answered_question_index + 1 if answered_question_index is not None else 1
                next_question_number = answered_question_number + 1

                # Pre-render next question HTML for client-side swap after viewing feedback
                next_question_html = templates.get_template("components/question.html").render(
                    {
                        "request": request,
                        "question": answer_result.next_question,
                        "date": date,
                        "question_number": next_question_number,
                        "total_questions": answer_result.total_questions,
                    }
                )

                # Render answer-result template showing answered question with highlights
                return templates.TemplateResponse(
                    request,
                    name="components/answer-result.html",
                    context={
                        "request": request,
                        "answered_question": answered_question,
                        "user_answer": answer_choice,
                        "correct_answer": answer_result.correct_answer,
                        "is_correct": answer_result.is_correct,
                        "question_number": answered_question_number,  # Actual question number
                        "current_score": answer_result.current_score,
                        "total_questions": answer_result.total_questions,
                        "next_question_html": next_question_html,
                        "date": date,
                    },
                )
            else:
                # Fallback: Just show next question directly (no feedback)
                return templates.TemplateResponse(
                    request,
                    name="components/question.html",
                    context={
                        "request": request,
                        "question": answer_result.next_question,
                        "date": date,
                        "question_number": answer_result.current_score + 1,
                        "total_questions": answer_result.total_questions,
                    },
                )
        else:
            # All questions answered - show feedback for last question, then completion
            # Get player state to find the last question they just answered
            player_state = await handle.query(PlayerEntityWorkflow.get_current_state)
            current_questions = player_state.current_questions or []

            # Find the answered question by ID and its position
            answered_question = None
            answered_question_index = None
            for i, q in enumerate(current_questions):
                if q.id == question_id:
                    answered_question = q
                    answered_question_index = i
                    break

            # If we found the answered question AND show_correct_answer is enabled, show feedback
            if answered_question and config.show_correct_answer:
                # Calculate question number (1-based)
                answered_question_number = answered_question_index + 1 if answered_question_index is not None else answer_result.total_questions

                # Pre-render completion page HTML for client-side swap after viewing feedback
                completion_html = templates.get_template("components/completion.html").render(
                    {
                        "request": request,
                        "completion_message": answer_result.completion_message,
                        "score": answer_result.current_score,
                        "total": answer_result.total_questions,
                        "date": date,
                    }
                )

                # Render answer-result template showing final question with highlights
                return templates.TemplateResponse(
                    request,
                    name="components/answer-result.html",
                    context={
                        "request": request,
                        "answered_question": answered_question,
                        "user_answer": answer_choice,
                        "correct_answer": answer_result.correct_answer,
                        "is_correct": answer_result.is_correct,
                        "question_number": answered_question_number,
                        "current_score": answer_result.current_score,
                        "total_questions": answer_result.total_questions,
                        "next_question_html": completion_html,  # Completion instead of next question
                        "is_last_question": True,  # Signal to show "View Results" instead of "Next Question"
                        "date": date,
                    },
                )
            else:
                # Fallback: Show completion directly (no feedback)
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
