# ABOUTME: PlayerEntityWorkflow maintains per-player state across entire event.
# Handles answer submission, score tracking, and progress queries for individual players.

from datetime import timedelta
from typing import cast

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from src.models.answer import AnswerResult, SubmitAnswerRequest
    from src.models.player import Player
    from src.models.question import Question
    from src.models.state import PlayerState


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
    async def run(self, player_id: str, email: str, first_name: str, last_name: str) -> None:
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
        self.state = PlayerState(player=player, current_day=None, current_question_index=0)

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
            current_questions=(list(self.state.current_questions) if self.state.current_questions else None),
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
            raise ApplicationError(f"Day {date} already completed")

        # Import activity class
        from src.activities.questions import QuestionsActivities

        # Call activity to get questions for the day
        questions = await workflow.execute_activity_method(
            QuestionsActivities.get_questions_for_day,
            args=[file_path, date],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Store questions in workflow state
        self.state.current_questions = questions
        self.state.current_day = date
        self.state.current_question_index = 0

        # Return first question
        return questions[0]

    @workflow.update
    async def submit_answer(self, request: SubmitAnswerRequest) -> AnswerResult:
        """Update handler to submit an answer and progress through questions.

        Validates the answer, updates scores if correct, and returns either the next
        question or a completion message if all questions have been answered.

        Args:
            request: SubmitAnswerRequest containing date, question_id, answer_choice,
                show_correct_answer

        Returns:
            AnswerResult: Contains feedback, next question or completion message, and scores

        Raises:
            RuntimeError: If workflow state is not initialized
            ValueError: If validations fail (invalid date, answer choice, question_id, etc.)

        Example:
            >>> # Submit correct answer
            >>> request = SubmitAnswerRequest("2025-03-10", "q1", "B", False)
            >>> result = await handle.execute_update(
            ...     PlayerEntityWorkflow.submit_answer, request
            ... )
            >>> assert result.is_correct is True
            >>> assert result.next_question is not None
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Validate day has been started
        if self.state.current_day is None:
            raise ApplicationError("Day not started - call start_day first")

        # Validate date matches current_day
        if request.date != self.state.current_day:
            raise ApplicationError(f"Date {request.date} does not match current day {self.state.current_day}")

        # Validate day not already completed
        if request.date in self.state.player.completed_days:
            raise ApplicationError(f"Day {request.date} already completed")

        # Validate answer_choice is valid
        if request.answer_choice not in ["A", "B", "C", "D"]:
            raise ApplicationError(f"Invalid answer_choice '{request.answer_choice}' - must be A, B, C, or D")

        # Get current question
        current_question = self._get_current_question()

        # Validate question_id matches current question
        if request.question_id != current_question.id:
            raise ApplicationError(
                f"Question ID {request.question_id} does not match current question {current_question.id}"
            )

        # Check if answer is correct
        is_correct = self._is_answer_correct(current_question, request.answer_choice)

        # Update scores if correct
        if is_correct:
            # Increment daily score
            self.state.player.daily_scores[request.date] = self.state.player.daily_scores.get(request.date, 0) + 1
            # Increment total score
            self.state.player.total_score += 1

        # Get current score and total questions
        current_score = self.state.player.daily_scores.get(request.date, 0)
        total_questions = len(self.state.current_questions) if self.state.current_questions else 0

        # Increment question index
        self.state.current_question_index += 1

        # Check if more questions remain
        if self.state.current_question_index < total_questions:
            # More questions remain - return next question
            # Cast safe: _get_current_question() validates current_questions is not None
            next_question = cast(list[Question], self.state.current_questions)[self.state.current_question_index]
            return AnswerResult(
                is_correct=is_correct,
                correct_answer=(current_question.correct_answer if request.show_correct_answer else None),
                next_question=next_question,
                completion_message=None,
                current_score=current_score,
                total_questions=total_questions,
            )
        else:
            # All questions answered - mark day as completed
            self.state.player.completed_days.add(request.date)

            # Submit score to DailyWorkflow for leaderboard aggregation via activity
            from src.activities.leaderboard import LeaderboardActivities
            from src.models.answer import SubmitScoreRequest

            # Calculate DailyWorkflow ID using predictable format: {event_id}-day-{date}
            parent_info = workflow.info().parent
            event_id = parent_info.workflow_id if parent_info is not None else "marathon-trivia-event"
            daily_workflow_id = f"{event_id}-day-{request.date}"

            # Call activity to submit score to DailyWorkflow
            # Activities can use the full Temporal client API to call updates on other workflows
            await workflow.execute_activity_method(
                LeaderboardActivities.submit_score_to_daily_workflow,
                args=[
                    daily_workflow_id,
                    SubmitScoreRequest(
                        player_id=self.state.player.id,
                        score=current_score,
                        first_name=self.state.player.first_name,
                        last_name=self.state.player.last_name,
                        email=self.state.player.email,
                    ),
                ],
                start_to_close_timeout=timedelta(seconds=10),
            )

            completion_message = f"Day complete! You scored {current_score}/{total_questions}."
            return AnswerResult(
                is_correct=is_correct,
                correct_answer=(current_question.correct_answer if request.show_correct_answer else None),
                next_question=None,
                completion_message=completion_message,
                current_score=current_score,
                total_questions=total_questions,
            )

    def _get_current_question(self) -> Question:
        """Helper method to get the current question from state.

        Returns:
            Question: The current question based on current_question_index

        Raises:
            RuntimeError: If workflow state not initialized or no questions loaded
            IndexError: If current_question_index is out of bounds
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        if self.state.current_questions is None:
            raise RuntimeError("No questions loaded - call start_day first")

        if self.state.current_question_index >= len(self.state.current_questions):
            raise IndexError("Current question index out of bounds")

        return self.state.current_questions[self.state.current_question_index]

    def _is_answer_correct(self, question: Question, answer: str) -> bool:
        """Helper method to check if an answer is correct.

        Args:
            question: The question being answered
            answer: The answer choice (A, B, C, or D)

        Returns:
            bool: True if answer matches question's correct_answer, False otherwise
        """
        return answer == question.correct_answer
