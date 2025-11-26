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


async def start_test_event_workflow(
    workflow_id: str, config_path: str = "tests/fixtures/config.toml"
) -> str:
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

    request = RegisterPlayerRequest(
        email=email, first_name=first_name, last_name=last_name
    )

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
    questions: list[Question],
    correct_answers: dict[str, str],
) -> int:
    """
    Answer all questions for a day.

    Args:
        player_id: Player workflow ID
        day_date: Date string (ISO format: YYYY-MM-DD)
        questions: List of questions for the day
        correct_answers: Dict mapping question_id to correct answer (A/B/C/D)

    Returns:
        Final score for the day

    Raises:
        Exception: If answering fails
    """
    score = 0

    for question in questions:
        correct_answer = correct_answers.get(question.id, "A")

        result = await submit_player_answer(
            player_id=player_id,
            date=day_date,
            question_id=question.id,
            answer_choice=correct_answer,
            show_correct_answer=True,
        )

        if result.is_correct:
            score += 1

    return score


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
