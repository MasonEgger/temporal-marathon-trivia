# ABOUTME: DailyWorkflow manages a single day's trivia session.
# Maintains daily leaderboard and receives score updates from players.

from temporalio import workflow

from src.models.config import EventConfig
from src.models.leaderboard import LeaderboardEntry
from src.models.question import Question
from src.models.state import DailyState


@workflow.defn
class DailyWorkflow:
    """Daily Workflow manages a single day's trivia session.

    This workflow:
    - Runs for one day of the event
    - Maintains daily leaderboard state
    - Receives score updates from PlayerEntityWorkflows
    - Provides queries for leaderboard and day active status

    State:
        state: DailyState containing date, questions, scores, and config.

    Queries:
        get_daily_leaderboard() -> list[LeaderboardEntry]: Returns current leaderboard.
        is_day_active() -> bool: Checks if current time is within day start/end bounds.

    Example:
        # Start workflow for March 10, 2025
        await client.start_workflow(
            DailyWorkflow.run,
            args=["2025-03-10", questions, config],
            id="daily-2025-03-10",
            task_queue="marathon-trivia",
        )
    """

    def __init__(self) -> None:
        """Initialize DailyWorkflow with no state."""
        self.state: DailyState | None = None

    @workflow.run
    async def run(self, date: str, questions: list[Question], config: EventConfig) -> None:
        """Run method that initializes state and keeps workflow running.

        Args:
            date: ISO format date string for this day (e.g., "2025-03-10").
            questions: List of Question objects for this day.
            config: EventConfig with timing and settings.

        Returns:
            None: This workflow runs indefinitely until externally terminated.
        """
        # Initialize state
        self.state = DailyState(
            date=date,
            questions=questions,
            player_scores={},
            completed_players=set(),
            config=config,
        )

        # Keep workflow running indefinitely (entity workflow pattern)
        await workflow.wait_condition(lambda: False)

    @workflow.query
    def get_daily_leaderboard(self) -> list[LeaderboardEntry]:
        """Query to retrieve the current daily leaderboard.

        Returns:
            list[LeaderboardEntry]: Empty list for now (ranking logic in Step 13).

        Raises:
            RuntimeError: If workflow state is not initialized.
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Return empty list for now - Step 13 will implement ranking logic
        return []

    @workflow.query
    def is_day_active(self) -> bool:
        """Query to check if the current time is within the day's active hours.

        Checks if workflow.now() is between day_start_time and day_end_time
        configured in EventConfig.

        Returns:
            bool: True if current time is within day bounds, False otherwise.

        Raises:
            RuntimeError: If workflow state is not initialized.
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")
        if self.state.config is None:
            raise RuntimeError("EventConfig not set in workflow state")

        # Get current workflow time
        current_time = workflow.now()

        # Extract time component (hour, minute, second) from workflow.now()
        current_time_of_day = current_time.time()

        # Compare with configured day bounds
        day_start = self.state.config.day_start_time
        day_end = self.state.config.day_end_time

        return day_start <= current_time_of_day <= day_end
