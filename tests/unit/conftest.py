# ABOUTME: Pytest fixtures for Temporal workflow unit tests.
# Provides reusable fixtures for WorkflowEnvironment, Client, Worker, and mock activities.

import concurrent.futures
from collections.abc import AsyncGenerator
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from temporalio import activity
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from src.models.answer import CreateTimezoneAwareDatetimeRequest, SubmitScoreRequest
from src.models.config import EventConfig
from src.models.question import Question
from src.workflows.daily import DailyWorkflow
from src.workflows.event import EventWorkflow
from src.workflows.player import PlayerEntityWorkflow

# ============================================================================
# Mock Activity Classes
# ============================================================================


class MockQuestionsActivities:
    """Mock questions activities for workflow testing."""

    @activity.defn(name="get_questions_for_day")
    def get_questions_for_day(self, file_path: str, date: str) -> list[Question]:
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


class MockConfigActivities:
    """Mock config activities for EventWorkflow testing."""

    @activity.defn(name="load_event_config")
    def load_event_config(self, config_path: str) -> EventConfig:
        """Mock load_event_config that returns test config."""
        return create_test_event_config()

    @activity.defn(name="validate_questions_file")
    def validate_questions_file(self, file_path: str, config: EventConfig) -> None:
        """Mock validate_questions_file that always succeeds."""
        pass


class MockEmailActivities:
    """Mock email activities for EventWorkflow testing."""

    @activity.defn(name="validate_email")
    def validate_email(self, email: str, require_work_email: bool) -> bool:
        """Mock validate_email that accepts all emails except invalid@blocked.com."""
        # For testing: reject "invalid@blocked.com" to test validation failure
        if email == "invalid@blocked.com":
            return False
        return True


class MockLeaderboardActivities:
    """Mock leaderboard activities for PlayerEntityWorkflow testing."""

    @activity.defn(name="submit_score_to_daily_workflow")
    def submit_score_to_daily_workflow(
        self, daily_workflow_id: str, request: SubmitScoreRequest
    ) -> None:
        """Mock submit_score_to_daily_workflow that does nothing (score submission tested separately)."""
        # In tests, we don't need to actually submit scores to DailyWorkflow
        # The activity execution is what we're testing
        pass


class MockTimeActivities:
    """Mock time activities for EventWorkflow testing."""

    @activity.defn(name="create_timezone_aware_datetime")
    def create_timezone_aware_datetime(self, request: CreateTimezoneAwareDatetimeRequest) -> datetime:
        """Mock create_timezone_aware_datetime for testing.

        Returns a timezone-aware datetime. For testing, we return a datetime
        in the past so workflows start immediately without waiting.
        """
        # Parse date and create datetime with timezone
        event_date = date.fromisoformat(request.date_str)
        time_obj = time(hour=request.time_hour, minute=request.time_minute)
        tz = ZoneInfo(request.timezone)
        return datetime.combine(event_date, time_obj, tzinfo=tz)


# ============================================================================
# Test Helper Functions
# ============================================================================


def create_test_event_config() -> EventConfig:
    """Create a test EventConfig for use in workflow tests.

    Returns:
        EventConfig with standard test values for a 3-day event.
    """
    return EventConfig(
        start_date=date(2025, 3, 10),
        end_date=date(2025, 3, 12),
        day_start_time=time(9, 0),
        day_end_time=time(17, 0),
        timezone="America/Los_Angeles",
        questions_file_path="config/questions.json",
        questions_per_day=5,
        show_correct_answer=True,
        require_work_email=False,
        s3_bucket_name="test-bucket",
        s3_region="us-west-2",
    )


def create_test_questions() -> list[Question]:
    """Create a list of test questions for use in workflow tests.

    Returns:
        List of 3 test Question instances.
    """
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


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def temporal_env() -> AsyncGenerator[WorkflowEnvironment]:
    """Create time-skipping Temporal test environment.

    Yields:
        WorkflowEnvironment configured for time-skipping (unit tests).
    """
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


@pytest_asyncio.fixture
async def client(temporal_env: WorkflowEnvironment) -> Client:
    """Get Temporal client with pydantic data converter configured.

    Args:
        temporal_env: The workflow environment fixture.

    Returns:
        Client instance configured with pydantic_data_converter.
    """
    new_config = temporal_env.client.config()
    new_config["data_converter"] = pydantic_data_converter
    return Client(**new_config)


@pytest.fixture
def mock_config_activities() -> MockConfigActivities:
    """Return mock config activities instance.

    Returns:
        MockConfigActivities instance for testing.
    """
    return MockConfigActivities()


@pytest.fixture
def mock_questions_activities() -> MockQuestionsActivities:
    """Return mock questions activities instance.

    Returns:
        MockQuestionsActivities instance for testing.
    """
    return MockQuestionsActivities()


@pytest.fixture
def mock_email_activities() -> MockEmailActivities:
    """Return mock email activities instance.

    Returns:
        MockEmailActivities instance for testing.
    """
    return MockEmailActivities()


@pytest.fixture
def mock_leaderboard_activities() -> MockLeaderboardActivities:
    """Return mock leaderboard activities instance.

    Returns:
        MockLeaderboardActivities instance for testing.
    """
    return MockLeaderboardActivities()


@pytest.fixture
def mock_time_activities() -> MockTimeActivities:
    """Return mock time activities instance.

    Returns:
        MockTimeActivities instance for testing.
    """
    return MockTimeActivities()


@pytest_asyncio.fixture
async def worker(
    client: Client,
    mock_config_activities: MockConfigActivities,
    mock_questions_activities: MockQuestionsActivities,
    mock_email_activities: MockEmailActivities,
    mock_leaderboard_activities: MockLeaderboardActivities,
    mock_time_activities: MockTimeActivities,
) -> AsyncGenerator[Worker]:
    """Create worker with ALL workflows and ALL mock activities registered.

    This is a catch-all worker fixture that registers all 3 workflows and all
    6 mock activity methods. Tests can use this single fixture without needing
    to specify which workflows/activities they need.

    Args:
        client: Temporal client fixture.
        mock_config_activities: Mock config activities fixture.
        mock_questions_activities: Mock questions activities fixture.
        mock_email_activities: Mock email activities fixture.
        mock_leaderboard_activities: Mock leaderboard activities fixture.
        mock_time_activities: Mock time activities fixture.

    Yields:
        Worker instance with all workflows and activities registered.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        async with Worker(
            client,
            task_queue="test-queue",
            workflows=[EventWorkflow, DailyWorkflow, PlayerEntityWorkflow],
            activities=[
                mock_config_activities.load_event_config,
                mock_config_activities.validate_questions_file,
                mock_questions_activities.get_questions_for_day,
                mock_email_activities.validate_email,
                mock_leaderboard_activities.submit_score_to_daily_workflow,
                mock_time_activities.create_timezone_aware_datetime,
            ],
            activity_executor=activity_executor,
        ) as worker:
            yield worker
