# ABOUTME: Unit tests for Marathon Trivia workflows (Player, Daily, Event).
# Tests state management, queries, update handlers using Temporal testing framework.

import uuid

import pytest
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.models.player import PlayerState
from src.workflows.player import PlayerEntityWorkflow


class TestPlayerEntityWorkflow:
    """Test suite for PlayerEntityWorkflow - basic structure and state management."""

    @pytest.mark.asyncio
    async def test_workflow_can_be_started_with_player_info(self) -> None:
        """Test that PlayerEntityWorkflow can be started with player information."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Configure client with pydantic data converter
            from temporalio.client import Client

            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )
                # Workflow should be running
                assert handle is not None

    @pytest.mark.asyncio
    async def test_workflow_initializes_with_correct_player_state(self) -> None:
        """Test that PlayerEntityWorkflow initializes with zero scores and empty completed days."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Configure client with pydantic data converter
            from temporalio.client import Client

            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )
                # Query current state
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert state.player.id == "player-123"
                assert state.player.email == "alice@example.com"
                assert state.player.first_name == "Alice"
                assert state.player.last_name == "Smith"
                assert state.player.total_score == 0
                assert state.player.daily_scores == {}
                assert state.player.completed_days == set()
                assert state.current_day is None
                assert state.current_question_index == 0

    @pytest.mark.asyncio
    async def test_query_get_current_state_returns_player_state(self) -> None:
        """Test that get_current_state query returns PlayerState."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Configure client with pydantic data converter
            from temporalio.client import Client

            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )
                # Query should return PlayerState instance
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert isinstance(state, PlayerState)

    @pytest.mark.asyncio
    async def test_query_get_score_for_day_returns_zero_initially(self) -> None:
        """Test that get_score_for_day query returns 0 for unplayed days."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Configure client with pydantic data converter
            from temporalio.client import Client

            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )
                # Score for any day should be 0 initially
                score = await handle.query(
                    PlayerEntityWorkflow.get_score_for_day, "2025-03-10"
                )
                assert score == 0

    @pytest.mark.asyncio
    async def test_query_has_completed_day_returns_false_initially(self) -> None:
        """Test that has_completed_day query returns False for unplayed days."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            # Configure client with pydantic data converter
            from temporalio.client import Client

            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )
                # No days should be completed initially
                completed = await handle.query(
                    PlayerEntityWorkflow.has_completed_day, "2025-03-10"
                )
                assert completed is False
