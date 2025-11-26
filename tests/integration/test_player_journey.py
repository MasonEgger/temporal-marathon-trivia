# ABOUTME: Integration tests for full player journey with real Temporal server.
# Tests complete player flows: registration, answering questions, and leaderboard visibility.

import asyncio
import uuid

import pytest

from tests.fixtures.temporal_test_helpers import (
    cleanup_workflow,
    get_event_status,
    get_player_state,
    register_test_player,
    start_player_day,
    start_test_event_workflow,
    submit_player_answer,
)


@pytest.mark.asyncio
async def test_player_can_join_answer_questions_and_see_leaderboard() -> None:
    """
    Test that a player can complete the full journey:
    1. Register via EventWorkflow
    2. Start a day and receive first question
    3. Answer all questions for the day
    4. Verify score is updated
    5. Verify day is marked completed
    """
    # Generate unique workflow ID
    workflow_id = f"test-event-{uuid.uuid4()}"

    try:
        # Start EventWorkflow
        await start_test_event_workflow(workflow_id)

        # Wait for workflow to initialize
        await asyncio.sleep(0.5)

        # Register player
        player_id = await register_test_player(
            event_workflow_id=workflow_id,
            email="alice@example.com",
            first_name="Alice",
            last_name="Smith",
        )

        assert player_id is not None
        assert isinstance(player_id, str)

        # Wait for player workflow to initialize
        await asyncio.sleep(0.5)

        # Start day 1
        first_question = await start_player_day(
            player_id=player_id, day_date="2025-03-10"
        )

        assert first_question is not None
        assert first_question.id == "day1_q1"
        assert first_question.text == "What does EC2 stand for in AWS?"

        # Answer first question (correct)
        result = await submit_player_answer(
            player_id=player_id,
            date="2025-03-10",
            question_id="day1_q1",
            answer_choice="A",  # Correct answer
            show_correct_answer=True,
        )

        assert result.is_correct is True
        assert result.next_question is not None
        assert result.next_question.id == "day1_q2"
        assert result.current_score == 1

        # Answer remaining questions (all correct)
        correct_answers = {
            "day1_q2": "B",  # S3
            "day1_q3": "B",  # 100 buckets
            "day1_q4": "C",  # DynamoDB
            "day1_q5": "A",  # Virtual Private Cloud
        }

        for q_id, answer in correct_answers.items():
            result = await submit_player_answer(
                player_id=player_id,
                date="2025-03-10",
                question_id=q_id,
                answer_choice=answer,
                show_correct_answer=True,
            )

            if q_id == "day1_q5":
                # Last question
                assert result.next_question is None
                assert result.completion_message is not None
                assert result.current_score == 5  # All 5 correct
            else:
                assert result.next_question is not None

        # Verify player state
        state = await get_player_state(player_id)

        assert state.player.total_score == 5
        assert state.player.daily_scores["2025-03-10"] == 5
        assert "2025-03-10" in state.player.completed_days

        # Verify event status shows player registered
        event_status = await get_event_status(workflow_id)

        assert event_status.player_count == 1

    finally:
        # Cleanup: Terminate workflows
        await cleanup_workflow(workflow_id)
        if "player_id" in locals():
            await cleanup_workflow(player_id)


@pytest.mark.asyncio
async def test_player_can_play_multiple_days() -> None:
    """
    Test that a player can complete multiple days:
    1. Register player
    2. Complete day 1 with perfect score
    3. Complete day 2 with partial score
    4. Verify total_score accumulates correctly
    5. Verify daily_scores has entries for both days
    """
    # Generate unique workflow ID
    workflow_id = f"test-event-{uuid.uuid4()}"

    try:
        # Start EventWorkflow
        await start_test_event_workflow(workflow_id)
        await asyncio.sleep(0.5)

        # Register player
        player_id = await register_test_player(
            event_workflow_id=workflow_id,
            email="bob@example.com",
            first_name="Bob",
            last_name="Jones",
        )

        await asyncio.sleep(0.5)

        # === DAY 1: Answer all questions correctly ===
        first_question_day1 = await start_player_day(
            player_id=player_id, day_date="2025-03-10"
        )

        assert first_question_day1.id == "day1_q1"

        # Answer all day 1 questions correctly
        day1_correct_answers = {
            "day1_q1": "A",
            "day1_q2": "B",
            "day1_q3": "B",
            "day1_q4": "C",
            "day1_q5": "A",
        }

        for q_id, answer in day1_correct_answers.items():
            await submit_player_answer(
                player_id=player_id,
                date="2025-03-10",
                question_id=q_id,
                answer_choice=answer,
            )

        # Verify day 1 completion
        state_after_day1 = await get_player_state(player_id)

        assert state_after_day1.player.total_score == 5
        assert state_after_day1.player.daily_scores["2025-03-10"] == 5
        assert "2025-03-10" in state_after_day1.player.completed_days

        # === DAY 2: Answer some questions incorrectly ===
        first_question_day2 = await start_player_day(
            player_id=player_id, day_date="2025-03-11"
        )

        assert first_question_day2.id == "day2_q1"

        # Answer day 2 questions (3 correct, 2 incorrect)
        day2_answers = {
            "day2_q1": "C",  # Correct: Lambda
            "day2_q2": "A",  # Incorrect (correct is C: 15 minutes)
            "day2_q3": "B",  # Correct: CloudFront
            "day2_q4": "D",  # Correct: Both A and B
            "day2_q5": "A",  # Incorrect (correct is B: Route 53)
        }

        for q_id, answer in day2_answers.items():
            await submit_player_answer(
                player_id=player_id,
                date="2025-03-11",
                question_id=q_id,
                answer_choice=answer,
            )

        # Verify day 2 completion and total accumulation
        state_after_day2 = await get_player_state(player_id)

        assert state_after_day2.player.daily_scores["2025-03-11"] == 3  # 3 correct
        assert state_after_day2.player.total_score == 8  # 5 + 3
        assert "2025-03-11" in state_after_day2.player.completed_days
        assert len(state_after_day2.player.completed_days) == 2

    finally:
        # Cleanup
        await cleanup_workflow(workflow_id)
        if "player_id" in locals():
            await cleanup_workflow(player_id)


@pytest.mark.asyncio
async def test_duplicate_email_returns_existing_player() -> None:
    """
    Test that registering with a duplicate email returns the existing player ID:
    1. Register player with email
    2. Register again with same email
    3. Verify same player_id is returned
    4. Verify player_count doesn't increase
    """
    # Generate unique workflow ID
    workflow_id = f"test-event-{uuid.uuid4()}"

    try:
        # Start EventWorkflow
        await start_test_event_workflow(workflow_id)
        await asyncio.sleep(0.5)

        # Register player first time
        player_id_1 = await register_test_player(
            event_workflow_id=workflow_id,
            email="charlie@example.com",
            first_name="Charlie",
            last_name="Brown",
        )

        # Verify player registered
        event_status_1 = await get_event_status(workflow_id)
        assert event_status_1.player_count == 1

        # Register player second time with SAME email
        player_id_2 = await register_test_player(
            event_workflow_id=workflow_id,
            email="charlie@example.com",  # Same email
            first_name="Charlie",  # Could even be different name
            last_name="Brown",
        )

        # Verify same player_id returned
        assert player_id_1 == player_id_2

        # Verify player_count did NOT increase
        event_status_2 = await get_event_status(workflow_id)
        assert event_status_2.player_count == 1  # Still 1, not 2

    finally:
        # Cleanup
        await cleanup_workflow(workflow_id)
        if "player_id_1" in locals():
            await cleanup_workflow(player_id_1)
