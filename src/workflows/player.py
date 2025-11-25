# ABOUTME: PlayerEntityWorkflow maintains per-player state across entire event.
# Handles answer submission, score tracking, and progress queries for individual players.

from datetime import timedelta

from temporalio import workflow

from src.models.player import Player, PlayerState
from src.models.question import Question


@workflow.defn
class PlayerEntityWorkflow:
    """Long-running entity workflow that maintains state for a single player across entire event.

    This workflow persists for the duration of the event and tracks:
    - Player identity (email, name)
    - Score accumulation across multiple days
    - Current progress within a day
    - Completed days

    The workflow never completes until the event ends, using workflow.wait_condition
    to keep it running indefinitely while responding to queries and update handlers.
    """

    def __init__(self) -> None:
        """Initialize workflow with empty state."""
        self.state: PlayerState | None = None

    @workflow.run
    async def run(
        self, player_id: str, email: str, first_name: str, last_name: str
    ) -> None:
        """Run method initializes player state and waits indefinitely.

        Args:
            player_id: Unique identifier for the player
            email: Player's email address
            first_name: Player's first name
            last_name: Player's last name

        Note:
            This workflow runs indefinitely using workflow.wait_condition(lambda: False)
            to keep the entity workflow alive for the entire event duration.
        """
        # Initialize player with provided information
        player = Player(
            id=player_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            total_score=0,
            daily_scores={},
            completed_days=set(),
            current_question_index={},
        )

        # Initialize workflow state
        self.state = PlayerState(
            player=player, current_day=None, current_question_index=0
        )

        # Keep workflow running indefinitely
        await workflow.wait_condition(lambda: False)

    @workflow.query
    def get_current_state(self) -> PlayerState:
        """Query method to get current player state.

        Returns:
            PlayerState: Copy of current state (defensive copy to prevent external mutation)

        Raises:
            RuntimeError: If workflow state is not initialized
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Return defensive copy to prevent external mutation
        return PlayerState(
            player=Player(
                id=self.state.player.id,
                email=self.state.player.email,
                first_name=self.state.player.first_name,
                last_name=self.state.player.last_name,
                total_score=self.state.player.total_score,
                daily_scores=dict(self.state.player.daily_scores),
                completed_days=set(self.state.player.completed_days),
                current_question_index=dict(self.state.player.current_question_index),
            ),
            current_day=self.state.current_day,
            current_question_index=self.state.current_question_index,
            current_questions=(
                list(self.state.current_questions) if self.state.current_questions else None
            ),
        )

    @workflow.query
    def get_score_for_day(self, date: str) -> int:
        """Query method to get player's score for a specific day.

        Args:
            date: Date string in ISO format (e.g., "2025-03-10")

        Returns:
            int: Score for the specified day (0 if day not played)

        Raises:
            RuntimeError: If workflow state is not initialized
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        return self.state.player.daily_scores.get(date, 0)

    @workflow.query
    def has_completed_day(self, date: str) -> bool:
        """Query method to check if player has completed a specific day.

        Args:
            date: Date string in ISO format (e.g., "2025-03-10")

        Returns:
            bool: True if day is completed, False otherwise

        Raises:
            RuntimeError: If workflow state is not initialized
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        return date in self.state.player.completed_days

    @workflow.update
    async def start_day(self, date: str, file_path: str = "config/questions.json") -> Question:
        """Update handler to start a new day of questions.

        Loads questions for the specified date via activity and returns the first question.
        Sets the current_day and resets current_question_index to 0.

        Args:
            date: Date string in ISO format (e.g., "2025-03-10")
            file_path: Path to questions JSON file (default: "config/questions.json")

        Returns:
            Question: The first question for the specified date

        Raises:
            RuntimeError: If workflow state is not initialized
            ValueError: If day is already completed

        Example:
            >>> # In workflow execution
            >>> first_question = await handle.execute_update(
            ...     PlayerEntityWorkflow.start_day, "2025-03-10"
            ... )
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Check if day already completed
        if date in self.state.player.completed_days:
            raise ValueError(f"Day {date} already completed")

        # Import activity class
        from src.activities.questions import QuestionsActivities

        # Call activity to get questions for the day
        questions_activities = QuestionsActivities()
        questions = await workflow.execute_activity_method(
            questions_activities.get_questions_for_day,
            args=[file_path, date],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Store questions in workflow state
        self.state.current_questions = questions
        self.state.current_day = date
        self.state.current_question_index = 0

        # Return first question
        return questions[0]
