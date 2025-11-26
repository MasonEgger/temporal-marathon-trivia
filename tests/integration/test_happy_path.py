# ABOUTME: Simple happy path integration test to verify basic gameplay.
# Tests one player answering all questions for one day, letting workflows complete naturally.

import asyncio
import uuid

import pytest

from tests.fixtures.temporal_test_helpers import (
    get_event_status,
    get_player_state,
    register_test_player,
    start_player_day,
    start_test_event_workflow,
    submit_player_answer,
)


@pytest.mark.asyncio
async def test_happy_path_single_player_single_day() -> None:
    """
    Happy path test: One player completes all questions for day 1.

    Expected workflows created:
    - 1 EventWorkflow: "test-parent-{short-uuid}" (stays running)
    - 3 DailyWorkflows: "test-parent-{short-uuid}-day1/2/3" (stays running)
    - 1 PlayerEntityWorkflow: "test-parent-{short-uuid}-player-AS-{short-uuid}" (stays running)

    Let workflows complete naturally - NO termination in cleanup.
    """
    # Use meaningful workflow ID with unique suffix
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"test-parent-{run_id}"

    # Start EventWorkflow
    print(f"\n=== Starting EventWorkflow: {workflow_id} ===")
    await start_test_event_workflow(workflow_id)

    # Wait for workflow to initialize and schedule daily workflows
    print("Waiting for EventWorkflow initialization...")
    await asyncio.sleep(1.0)

    # Verify event status
    event_status = await get_event_status(workflow_id)
    print(f"Event created: {event_status.event_id}")
    print(f"Daily workflows scheduled: {len(event_status.daily_workflow_ids)}")
    print(f"Daily workflow IDs: {list(event_status.daily_workflow_ids.keys())}")

    # Register player
    print("\n=== Registering Player ===")
    player_id = await register_test_player(
        event_workflow_id=workflow_id,
        email="alice@example.com",
        first_name="Alice",
        last_name="Smith",
    )
    print(f"Player registered: {player_id}")

    # Wait for player workflow to initialize
    await asyncio.sleep(0.5)

    # Start day 1
    print("\n=== Starting Day 1 (2025-03-10) ===")
    first_question = await start_player_day(player_id=player_id, day_date="2025-03-10")
    print(f"First question: {first_question.id} - {first_question.text}")

    # Answer all 5 questions correctly
    print("\n=== Answering Questions ===")
    correct_answers = [
        ("day1_q1", "A"),  # EC2
        ("day1_q2", "B"),  # S3
        ("day1_q3", "B"),  # 100 buckets
        ("day1_q4", "C"),  # DynamoDB
        ("day1_q5", "A"),  # VPC
    ]

    for i, (q_id, answer) in enumerate(correct_answers, 1):
        result = await submit_player_answer(
            player_id=player_id,
            date="2025-03-10",
            question_id=q_id,
            answer_choice=answer,
            show_correct_answer=True,
        )

        status = "✓ Correct" if result.is_correct else "✗ Incorrect"
        print(f"Question {i}/5: {q_id} - {status} - Score: {result.current_score}")

        if i == 5:
            # Last question
            assert result.next_question is None
            assert result.completion_message is not None
            print(f"Day complete! Message: {result.completion_message}")
        else:
            assert result.next_question is not None

    # Verify final player state
    print("\n=== Final Player State ===")
    state = await get_player_state(player_id)
    print(f"Total score: {state.player.total_score}")
    print(f"Daily scores: {state.player.daily_scores}")
    print(f"Completed days: {state.player.completed_days}")

    assert state.player.total_score == 5
    assert state.player.daily_scores["2025-03-10"] == 5
    assert "2025-03-10" in state.player.completed_days

    # Verify event status
    event_status = await get_event_status(workflow_id)
    assert event_status.player_count == 1

    print("\n=== Test Complete ===")
    print(f"EventWorkflow ID: {workflow_id}")
    print(f"PlayerEntityWorkflow ID: {player_id}")
    print("Check Temporal UI to see workflow states:")
    print(f"  http://localhost:8233/namespaces/default/workflows/{workflow_id}")
    print(f"  http://localhost:8233/namespaces/default/workflows/{player_id}")
    print("\nWorkflows left running - NO termination!")
