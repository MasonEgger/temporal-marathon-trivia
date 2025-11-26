# ABOUTME: Unit tests for Marathon Trivia workflows (Player, Daily, Event).
# Tests state management, queries, update handlers using Temporal testing framework.

import uuid

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowUpdateFailedError
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.models.answer import AnswerResult, SubmitAnswerRequest
from src.models.player import PlayerState
from src.models.question import Question
from src.workflows.player import PlayerEntityWorkflow


# Mock activity for testing
class MockQuestionsActivities:
    """Mock questions activities for workflow testing."""

    @activity.defn(name="get_questions_for_day")
    async def get_questions_for_day(self, file_path: str, date: str) -> list[Question]:
        """Mock get_questions_for_day that returns test questions."""
        # Return 3 test questions for any date
        return [
            Question(
                id="q1",
                text="What is 2+2?",
                options={"A": "3", "B": "4", "C": "5", "D": "6"},
                correct_answer="B",
            ),
            Question(
                id="q2",
                text="What is the capital of France?",
                options={"A": "London", "B": "Berlin", "C": "Paris", "D": "Madrid"},
                correct_answer="C",
            ),
            Question(
                id="q3",
                text="What color is the sky?",
                options={"A": "Red", "B": "Blue", "C": "Green", "D": "Yellow"},
                correct_answer="B",
            ),
        ]


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


class TestPlayerEntityWorkflowStartDay:
    """Test suite for PlayerEntityWorkflow start_day update handler."""

    @pytest.mark.asyncio
    async def test_start_day_returns_first_question(self) -> None:
        """Test that start_day returns the first Question for the specified date."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Call start_day update handler
                result = await handle.execute_update(
                    PlayerEntityWorkflow.start_day, "2025-03-10"
                )

                # Should return first question
                assert isinstance(result, Question)
                assert result.id == "q1"
                assert result.text == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_start_day_sets_current_day_in_state(self) -> None:
        """Test that start_day sets current_day in workflow state."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Call start_day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Query state to verify current_day is set
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert state.current_day == "2025-03-10"

    @pytest.mark.asyncio
    async def test_start_day_sets_current_question_index_to_zero(self) -> None:
        """Test that start_day sets current_question_index to 0."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Call start_day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Query state to verify current_question_index is 0
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert state.current_question_index == 0

    @pytest.mark.asyncio
    async def test_start_day_raises_error_if_day_already_completed(self) -> None:
        """Test that start_day raises error if day is already completed."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day and complete all questions
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q2", "C", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q3", "B", False),
                )

                # Try to start the same day again - should raise error
                with pytest.raises(WorkflowUpdateFailedError) as exc_info:
                    await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")
                assert "already completed" in str(exc_info.value.cause).lower()

    @pytest.mark.asyncio
    async def test_start_day_calls_get_questions_for_day_activity(self) -> None:
        """Test that start_day calls the get_questions_for_day activity."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Call start_day - if activity isn't called, this will fail
                result = await handle.execute_update(
                    PlayerEntityWorkflow.start_day, "2025-03-10"
                )

                # If we get a result, activity was called successfully
                assert result is not None

    @pytest.mark.asyncio
    async def test_start_day_returns_question_with_correct_structure(self) -> None:
        """Test that start_day returns a Question object with proper structure."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Call start_day
                result = await handle.execute_update(
                    PlayerEntityWorkflow.start_day, "2025-03-10"
                )

                # Verify Question structure
                assert isinstance(result, Question)
                assert hasattr(result, "id")
                assert hasattr(result, "text")
                assert hasattr(result, "options")
                assert hasattr(result, "correct_answer")
                assert len(result.options) == 4
                assert set(result.options.keys()) == {"A", "B", "C", "D"}


class TestPlayerEntityWorkflowSubmitAnswer:
    """Test suite for PlayerEntityWorkflow submit_answer update handler."""

    @pytest.mark.asyncio
    async def test_submit_answer_with_correct_answer_increments_score(self) -> None:
        """Test that submit_answer with correct answer increments daily and total score."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day first
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Submit correct answer (question q1, correct answer is "B")
                request = SubmitAnswerRequest(
                    date="2025-03-10",
                    question_id="q1",
                    answer_choice="B",  # correct
                    show_correct_answer=False,
                )
                result = await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer, request
                )

                # Verify result
                assert isinstance(result, AnswerResult)
                assert result.is_correct is True

                # Verify score updated
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert state.player.daily_scores.get("2025-03-10", 0) == 1
                assert state.player.total_score == 1

    @pytest.mark.asyncio
    async def test_submit_answer_with_incorrect_answer_does_not_increment_score(self) -> None:
        """Test that submit_answer with incorrect answer does not increment score."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Submit incorrect answer (question q1, correct answer is "B", submit "A")
                request = SubmitAnswerRequest(
                    date="2025-03-10",
                    question_id="q1",
                    answer_choice="A",  # incorrect
                    show_correct_answer=False,
                )
                result = await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer, request
                )

                # Verify result
                assert isinstance(result, AnswerResult)
                assert result.is_correct is False

                # Verify score NOT updated
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert state.player.daily_scores.get("2025-03-10", 0) == 0
                assert state.player.total_score == 0

    @pytest.mark.asyncio
    async def test_submit_answer_returns_next_question_if_more_remain(self) -> None:
        """Test that submit_answer returns next question if more questions remain."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Submit answer to first question
                request = SubmitAnswerRequest(
                    date="2025-03-10",
                    question_id="q1",
                    answer_choice="B",
                    show_correct_answer=False,
                )
                result = await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer, request
                )

                # Should return next question (q2)
                assert result.next_question is not None
                assert result.next_question.id == "q2"
                assert result.completion_message is None

    @pytest.mark.asyncio
    async def test_submit_answer_returns_completion_message_if_all_questions_answered(
        self,
    ) -> None:
        """Test that submit_answer returns completion message after last question."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Answer first two questions
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q2", "C", False),
                )

                # Answer last question
                result = await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q3", "B", False),
                )

                # Should return completion message, no next question
                assert result.next_question is None
                assert result.completion_message is not None
                assert isinstance(result.completion_message, str)

    @pytest.mark.asyncio
    async def test_submit_answer_validates_answer_choice_is_valid(self) -> None:
        """Test that submit_answer validates answer_choice is one of A, B, C, D."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Submit with invalid answer choice should raise error
                with pytest.raises(WorkflowUpdateFailedError) as exc_info:
                    await handle.execute_update(
                        PlayerEntityWorkflow.submit_answer,
                        SubmitAnswerRequest("2025-03-10", "q1", "E", False),
                    )
                assert "answer_choice" in str(exc_info.value.cause).lower()

    @pytest.mark.asyncio
    async def test_submit_answer_raises_error_if_question_id_does_not_match(self) -> None:
        """Test that submit_answer raises error if question_id doesn't match current question."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day (current question is q1)
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Submit with wrong question_id should raise error
                with pytest.raises(WorkflowUpdateFailedError) as exc_info:
                    await handle.execute_update(
                        PlayerEntityWorkflow.submit_answer,
                        SubmitAnswerRequest("2025-03-10", "q999", "B", False),
                    )
                assert "question" in str(exc_info.value.cause).lower()

    @pytest.mark.asyncio
    async def test_submit_answer_raises_error_if_day_not_started(self) -> None:
        """Test that submit_answer raises ValueError if day hasn't been started yet."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Don't start day, try to submit answer
                with pytest.raises(WorkflowUpdateFailedError) as exc_info:
                    await handle.execute_update(
                        PlayerEntityWorkflow.submit_answer,
                        SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                    )
                assert "not started" in str(exc_info.value.cause).lower()

    @pytest.mark.asyncio
    async def test_submit_answer_raises_error_if_day_already_completed(self) -> None:
        """Test that submit_answer raises ValueError if day is already completed."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day and complete all questions
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q2", "C", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q3", "B", False),
                )

                # Try to submit again after completion
                with pytest.raises(WorkflowUpdateFailedError) as exc_info:
                    await handle.execute_update(
                        PlayerEntityWorkflow.submit_answer,
                        SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                    )
                assert "completed" in str(exc_info.value.cause).lower()

    @pytest.mark.asyncio
    async def test_submit_answer_marks_day_as_completed_after_last_question(self) -> None:
        """Test that submit_answer marks day as completed after answering last question."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day and answer all questions
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q2", "C", False),
                )
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q3", "B", False),
                )

                # Verify day is marked as completed
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert "2025-03-10" in state.player.completed_days

    @pytest.mark.asyncio
    async def test_submit_answer_updates_total_score_correctly(self) -> None:
        """Test that submit_answer updates total_score correctly across questions."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            new_config = env.client.config()
            new_config["data_converter"] = pydantic_data_converter
            client = Client(**new_config)

            mock_activities = MockQuestionsActivities()
            async with Worker(
                client,
                task_queue="test-queue",
                workflows=[PlayerEntityWorkflow],
                activities=[mock_activities.get_questions_for_day],
            ):
                handle = await client.start_workflow(
                    PlayerEntityWorkflow.run,
                    args=["player-123", "alice@example.com", "Alice", "Smith"],
                    id=f"test-player-workflow-{uuid.uuid4()}",
                    task_queue="test-queue",
                )

                # Start day
                await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")

                # Answer 2 correct, 1 incorrect
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q1", "B", False),
                )  # correct
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q2", "A", False),
                )  # incorrect
                await handle.execute_update(
                    PlayerEntityWorkflow.submit_answer,
                    SubmitAnswerRequest("2025-03-10", "q3", "B", False),
                )  # correct

                # Verify total score is 2
                state = await handle.query(PlayerEntityWorkflow.get_current_state)
                assert state.player.total_score == 2
                assert state.player.daily_scores.get("2025-03-10", 0) == 2
