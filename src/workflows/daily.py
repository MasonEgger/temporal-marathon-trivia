# ABOUTME: DailyWorkflow manages a single day's trivia session.
# Maintains daily leaderboard and receives score updates from players.

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.models.answer import SubmitScoreRequest
    from src.models.config import EventConfig
    from src.models.leaderboard import LeaderboardEntry
    from src.models.question import Question
    from src.models.state import DailyState


def calculate_leaderboard(
    player_scores: dict[str, int],
    player_info: dict[str, tuple[str, str, str]],
) -> list[LeaderboardEntry]:
    """Calculate leaderboard with proper ranking, tie handling, and alphabetical sorting.

    Ranks players by score (descending), with ties broken alphabetically by last name,
    then first name. Players with the same score share the same rank, and the next rank
    adjusts accordingly (e.g., 5 players at rank 1 means the next player is rank 6).

    Args:
        player_scores: Mapping of player_id to score.
        player_info: Mapping of player_id to tuple of (email, first_name, last_name).

    Returns:
        list[LeaderboardEntry]: Sorted leaderboard entries with proper ranking.

    Example:
        >>> scores = {"p1": 5, "p2": 8, "p3": 3}
        >>> info = {
        ...     "p1": ("alice@example.com", "Alice", "Smith"),
        ...     "p2": ("bob@example.com", "Bob", "Johnson"),
        ...     "p3": ("charlie@example.com", "Charlie", "Williams"),
        ... }
        >>> leaderboard = calculate_leaderboard(scores, info)
        >>> leaderboard[0].total_score
        8
        >>> leaderboard[0].rank
        1
    """
    # Early return for empty leaderboard
    if not player_scores:
        return []

    # Create list of (player_id, score, last_name, first_name) for sorting
    player_data = []
    for player_id, score in player_scores.items():
        email, first_name, last_name = player_info[player_id]
        player_data.append((player_id, score, last_name, first_name, email))

    # Sort by score descending (-score), then last name ascending, then first name ascending
    player_data.sort(key=lambda x: (-x[1], x[2].lower(), x[3].lower()))

    # Assign ranks with tie handling
    leaderboard: list[LeaderboardEntry] = []
    current_rank = 1
    previous_score = None

    for i, (_player_id, score, last_name, first_name, email) in enumerate(player_data):
        # Determine rank
        if previous_score is None or score < previous_score:
            # New score tier - update rank to current position + 1
            current_rank = i + 1
        # else: same score as previous player - keep same rank

        # Create display name in "FirstName L." format
        display_name = f"{first_name} {last_name[0]}." if last_name else first_name

        # Create leaderboard entry
        entry = LeaderboardEntry(
            rank=current_rank,
            display_name=display_name,
            total_score=score,
            daily_scores={},  # Will be populated by API layer later
            email=email,
        )
        leaderboard.append(entry)

        # Track previous score for tie detection
        previous_score = score

    return leaderboard


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
    async def run(
        self, date: str, questions: list[Question], config: EventConfig
    ) -> None:
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
            list[LeaderboardEntry]: Sorted leaderboard with proper ranking, tie handling,
                and alphabetical sorting.

        Raises:
            RuntimeError: If workflow state is not initialized.
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Use calculate_leaderboard helper to compute rankings
        return calculate_leaderboard(self.state.player_scores, self.state.player_info)

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

    @workflow.update
    def submit_score(self, request: SubmitScoreRequest) -> None:
        """Update handler to receive and store player scores for this day.

        Stores the player's score and marks them as completed. Validation is done
        by the validator to prevent duplicate submissions from being written to history.

        Args:
            request: SubmitScoreRequest containing player_id, score, email, first_name, last_name.

        Example:
            >>> request = SubmitScoreRequest(
            ...     player_id="player-123",
            ...     score=8,
            ...     email="alice@example.com",
            ...     first_name="Alice",
            ...     last_name="Smith"
            ... )
            >>> await handle.execute_update(DailyWorkflow.submit_score, request)
        """
        # Validator ensures state is not None and player hasn't submitted yet
        # Store player info if not already stored
        if request.player_id not in self.state.player_info:  # type: ignore[union-attr]
            self.state.player_info[request.player_id] = (  # type: ignore[union-attr]
                request.email,
                request.first_name,
                request.last_name,
            )

        # Store score
        self.state.player_scores[request.player_id] = request.score  # type: ignore[union-attr]

        # Mark player as completed
        self.state.completed_players.add(request.player_id)  # type: ignore[union-attr]

    @submit_score.validator
    def validate_submit_score(self, request: SubmitScoreRequest) -> None:
        """Validator for submit_score update handler.

        Validates that the workflow state is initialized and that the player
        hasn't already submitted a score for this day. Rejects the update if
        validation fails, preventing it from being written to event history.

        Args:
            request: SubmitScoreRequest containing player_id and score details.

        Raises:
            ValueError: If workflow state is not initialized or player has already
                submitted a score for this day (duplicate).
        """
        if self.state is None:
            raise ValueError("Workflow state not initialized")

        # Reject duplicate submissions
        if request.player_id in self.state.completed_players:
            raise ValueError(
                f"Player {request.player_id} has already submitted a score for this day"
            )
