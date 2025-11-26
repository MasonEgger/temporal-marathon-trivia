# ABOUTME: Helper functions for integration tests with real Temporal server.
# Provides utilities for creating test events, players, and answering questions.

import os
from pathlib import Path

from dotenv import load_dotenv

from src.models.answer import RegisterPlayerRequest, SubmitAnswerRequest
from src.models.question import Question
from src.temporal_client import create_temporal_client
from src.workflows.event import EventWorkflow
from src.workflows.player import PlayerEntityWorkflow


def load_test_env() -> None:
    """Load environment variables from .env file for tests."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


async def get_temporal_client():
    """Get a Temporal client configured from environment."""
    load_test_env()
    return await create_temporal_client()


def get_task_queue() -> str:
    """Get the task queue from environment."""
    load_test_env()
    return os.getenv("TEMPORAL_TASK_QUEUE", "marathon-trivia")


async def start_test_event_workflow(workflow_id: str, config_path: str = "tests/fixtures/config.toml") -> str:
    """
    Start an EventWorkflow for integration testing.

    Args:
        workflow_id: Unique ID for the workflow
        config_path: Path to event configuration file

    Returns:
        The workflow ID

    Raises:
        Exception: If workflow cannot be started
    """
    client = await get_temporal_client()
    task_queue = get_task_queue()

    await client.start_workflow(
        EventWorkflow.run,
        args=[workflow_id, config_path],
        id=workflow_id,
        task_queue=task_queue,
    )

    return workflow_id


async def register_test_player(
    event_workflow_id: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    """
    Register a player via EventWorkflow.

    Args:
        event_workflow_id: ID of the EventWorkflow
        email: Player email
        first_name: Player first name
        last_name: Player last name

    Returns:
        Player ID

    Raises:
        Exception: If registration fails
    """
    client = await get_temporal_client()

    handle = client.get_workflow_handle(event_workflow_id)

    request = RegisterPlayerRequest(email=email, first_name=first_name, last_name=last_name)

    player_id = await handle.execute_update(EventWorkflow.register_player, request)

    return player_id


async def start_player_day(
    player_id: str, day_date: str, questions_file: str = "tests/fixtures/questions.json"
) -> Question:
    """
    Start a day for a player and get the first question.

    Args:
        player_id: Player workflow ID
        day_date: Date string (ISO format: YYYY-MM-DD)
        questions_file: Path to questions JSON file

    Returns:
        The first question for the day

    Raises:
        Exception: If day cannot be started
    """
    client = await get_temporal_client()

    handle = client.get_workflow_handle(player_id)

    first_question = await handle.execute_update(
        PlayerEntityWorkflow.start_day,
        args=[day_date, questions_file],
    )

    return first_question


async def submit_player_answer(
    player_id: str,
    date: str,
    question_id: str,
    answer_choice: str,
    show_correct_answer: bool = True,
):
    """
    Submit an answer for a player.

    Args:
        player_id: Player workflow ID
        date: Date string (ISO format: YYYY-MM-DD)
        question_id: Question ID being answered
        answer_choice: Answer choice (A, B, C, or D)
        show_correct_answer: Whether to show correct answer in response

    Returns:
        AnswerResult with answer feedback and next question or completion

    Raises:
        Exception: If answer submission fails
    """
    client = await get_temporal_client()

    handle = client.get_workflow_handle(player_id)

    request = SubmitAnswerRequest(
        date=date,
        question_id=question_id,
        answer_choice=answer_choice,
        show_correct_answer=show_correct_answer,
    )

    result = await handle.execute_update(PlayerEntityWorkflow.submit_answer, request)

    return result


async def answer_all_questions(
    player_id: str,
    day_date: str,
    questions: list[Question] | None = None,
    correct_answers: dict[str, str] | None = None,
    correct_count: int | None = None,
) -> list[Question]:
    """
    Answer all questions for a day.

    Args:
        player_id: Player workflow ID
        day_date: Date string (ISO format: YYYY-MM-DD)
        questions: List of questions for the day (if None, will start day to get them)
        correct_answers: Dict mapping question_id to correct answer (A/B/C/D)
        correct_count: Number of questions to answer correctly (simplified mode)

    Returns:
        List of questions that were answered

    Raises:
        Exception: If answering fails
    """
    # Simplified mode: answer first N questions correctly
    if correct_count is not None:
        # Start the day to get first question
        first_question = await start_player_day(
            player_id=player_id,
            day_date=day_date,
        )

        all_questions = [first_question]
        score = 0

        while True:
            current_question = all_questions[-1]

            # Determine if we should answer correctly
            should_be_correct = score < correct_count
            if should_be_correct:
                answer_choice = current_question.correct_answer
            else:
                # Choose a wrong answer
                answer_choice = "B" if current_question.correct_answer != "B" else "A"

            result = await submit_player_answer(
                player_id=player_id,
                date=day_date,
                question_id=current_question.id,
                answer_choice=answer_choice,
                show_correct_answer=True,
            )

            if result.is_correct:
                score += 1

            if result.next_question:
                all_questions.append(result.next_question)
            else:
                # Day completed - submit score to DailyWorkflow
                await submit_score_to_daily_workflow(
                    event_workflow_id=None,  # Will be fetched from player
                    player_id=player_id,
                    day_date=day_date,
                    score=score,
                )
                break

        return all_questions

    # Normal mode with correct_answers dict
    if questions is None:
        # Start the day to get first question
        first_question = await start_player_day(
            player_id=player_id,
            day_date=day_date,
        )
        questions = [first_question]

    score = 0
    for i, question in enumerate(questions):
        correct_answer = correct_answers.get(question.id, "A") if correct_answers else "A"

        result = await submit_player_answer(
            player_id=player_id,
            date=day_date,
            question_id=question.id,
            answer_choice=correct_answer,
            show_correct_answer=True,
        )

        if result.is_correct:
            score += 1

        # Get next question from result
        if result.next_question and i < len(questions) - 1:
            questions.append(result.next_question)

    return questions


async def submit_score_to_daily_workflow(
    event_workflow_id: str | None,
    player_id: str,
    day_date: str,
    score: int,
) -> None:
    """
    Submit a player's score to the DailyWorkflow.

    Args:
        event_workflow_id: ID of the EventWorkflow (if None, will query player to get it)
        player_id: Player workflow ID
        day_date: Date string (ISO format: YYYY-MM-DD)
        score: Final score for the day

    Raises:
        Exception: If submission fails
    """
    client = await get_temporal_client()

    # Get player state to retrieve email and name
    player_handle = client.get_workflow_handle(player_id)
    player_state = await player_handle.query(PlayerEntityWorkflow.get_current_state)

    # If event_workflow_id not provided, extract from player_id
    # Player IDs format: {event-id}-player-{initials}-{uuid}
    if event_workflow_id is None:
        parts = player_id.split("-player-")
        if len(parts) >= 1:
            event_workflow_id = parts[0]
        else:
            raise ValueError(f"Could not extract event_workflow_id from player_id: {player_id}")

    # Get daily workflow ID from event workflow
    event_handle = client.get_workflow_handle(event_workflow_id)
    event_status = await event_handle.query(EventWorkflow.get_event_status)
    daily_workflow_id = event_status.daily_workflow_ids.get(day_date)

    if not daily_workflow_id:
        raise ValueError(f"No DailyWorkflow found for date: {day_date}")

    # Submit score to DailyWorkflow
    from src.models.answer import SubmitScoreRequest

    request = SubmitScoreRequest(
        player_id=player_id,
        score=score,
        email=player_state.player.email,
        first_name=player_state.player.first_name,
        last_name=player_state.player.last_name,
    )

    daily_handle = client.get_workflow_handle(daily_workflow_id)
    from src.workflows.daily import DailyWorkflow

    await daily_handle.execute_update(DailyWorkflow.submit_score, request)


async def get_player_state(player_id: str):
    """
    Get the current state of a player workflow.

    Args:
        player_id: Player workflow ID

    Returns:
        PlayerState object

    Raises:
        Exception: If query fails
    """
    client = await get_temporal_client()

    handle = client.get_workflow_handle(player_id)

    state = await handle.query(PlayerEntityWorkflow.get_current_state)

    return state


async def get_event_status(event_workflow_id: str):
    """
    Get the status of an event workflow.

    Args:
        event_workflow_id: EventWorkflow ID

    Returns:
        EventStatusResponse with event metadata

    Raises:
        Exception: If query fails
    """
    client = await get_temporal_client()

    handle = client.get_workflow_handle(event_workflow_id)

    status = await handle.query(EventWorkflow.get_event_status)

    return status


async def cleanup_workflow(workflow_id: str) -> None:
    """
    Terminate a workflow for cleanup after tests.

    Args:
        workflow_id: Workflow ID to terminate

    Note:
        This forcibly terminates the workflow. Use only for test cleanup.
        Silently ignores if workflow is already completed.
    """
    from temporalio.service import RPCError, RPCStatusCode

    client = await get_temporal_client()

    handle = client.get_workflow_handle(workflow_id)

    try:
        await handle.terminate("Test cleanup")
    except RPCError as e:
        # Ignore if workflow already completed
        if e.status != RPCStatusCode.NOT_FOUND:
            raise
