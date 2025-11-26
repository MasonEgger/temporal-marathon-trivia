# ABOUTME: Request/response models for workflow update handlers.
# Contains models for answer submission and score submission with type safety.

from dataclasses import dataclass

from src.models.question import Question


@dataclass
class SubmitAnswerRequest:
    """Request model for submit_answer update handler.

    Encapsulates all parameters needed to submit an answer, maintaining
    type safety when passing to workflow update handlers.

    Attributes:
        date: Date string in ISO format (e.g., "2025-03-10")
        question_id: ID of the question being answered
        answer_choice: Answer choice (must be "A", "B", "C", or "D")
        show_correct_answer: Whether to include correct answer in response

    Example:
        >>> request = SubmitAnswerRequest(
        ...     date="2025-03-10",
        ...     question_id="q1",
        ...     answer_choice="B",
        ...     show_correct_answer=False
        ... )
        >>> result = await handle.execute_update(
        ...     PlayerEntityWorkflow.submit_answer, request
        ... )
    """

    date: str
    question_id: str
    answer_choice: str
    show_correct_answer: bool


@dataclass
class AnswerResult:
    """Result returned from submit_answer update handler.

    Contains feedback about the submitted answer and what to display next
    (either the next question or a completion message).

    Attributes:
        is_correct: Whether the submitted answer was correct
        correct_answer: The correct answer (A/B/C/D), only if show_correct_answer is True
        next_question: The next question to display, or None if day complete
        completion_message: Message to display if day complete, or None if more questions
        current_score: Player's current score for this day
        total_questions: Total number of questions for this day

    Example:
        >>> # Correct answer with next question
        >>> result = AnswerResult(
        ...     is_correct=True,
        ...     correct_answer=None,  # Not showing correct answers
        ...     next_question=Question(...),
        ...     completion_message=None,
        ...     current_score=1,
        ...     total_questions=5
        ... )
        >>>
        >>> # Last question with completion
        >>> result = AnswerResult(
        ...     is_correct=True,
        ...     correct_answer=None,
        ...     next_question=None,
        ...     completion_message="Great job! You scored 5/5!",
        ...     current_score=5,
        ...     total_questions=5
        ... )
    """

    is_correct: bool
    correct_answer: str | None
    next_question: Question | None
    completion_message: str | None
    current_score: int
    total_questions: int


@dataclass
class SubmitScoreRequest:
    """Request model for submit_score update handler in DailyWorkflow.

    Encapsulates all parameters needed to submit a player's score for a day,
    maintaining type safety when passing to workflow update handlers.

    Attributes:
        player_id: Unique identifier for the player
        score: The score achieved by the player for this day
        email: Player's email address
        first_name: Player's first name
        last_name: Player's last name

    Example:
        >>> request = SubmitScoreRequest(
        ...     player_id="player-123",
        ...     score=8,
        ...     email="alice@example.com",
        ...     first_name="Alice",
        ...     last_name="Smith"
        ... )
        >>> await handle.execute_update(
        ...     DailyWorkflow.submit_score, request
        ... )
    """

    player_id: str
    score: int
    email: str
    first_name: str
    last_name: str


@dataclass
class RegisterPlayerRequest:
    """Request model for register_player update handler in EventWorkflow.

    Encapsulates all parameters needed to register a new player,
    maintaining type safety when passing to workflow update handlers.

    Attributes:
        email: Player's email address (used for duplicate detection)
        first_name: Player's first name
        last_name: Player's last name
        company_name: Player's company name (optional)

    Example:
        >>> request = RegisterPlayerRequest(
        ...     email="john.doe@company.com",
        ...     first_name="John",
        ...     last_name="Doe",
        ...     company_name="Acme Corp"
        ... )
        >>> player_id = await handle.execute_update(
        ...     EventWorkflow.register_player, request
        ... )
    """

    email: str
    first_name: str
    last_name: str
    company_name: str | None = None


@dataclass
class CreateTimezoneAwareDatetimeRequest:
    """Request model for create_timezone_aware_datetime activity.

    Encapsulates all parameters needed to create a timezone-aware datetime,
    maintaining type safety when calling time conversion activities.

    Attributes:
        date_str: Date string in ISO format (e.g., "2025-03-10")
        time_hour: Hour component (0-23)
        time_minute: Minute component (0-59)
        timezone: IANA timezone string (e.g., "America/Los_Angeles")

    Example:
        >>> request = CreateTimezoneAwareDatetimeRequest(
        ...     date_str="2025-03-10",
        ...     time_hour=9,
        ...     time_minute=0,
        ...     timezone="America/Los_Angeles"
        ... )
        >>> dt = await workflow.execute_activity_method(
        ...     time_activities.create_timezone_aware_datetime, request
        ... )
    """

    date_str: str
    time_hour: int
    time_minute: int
    timezone: str


@dataclass
class EventStatusResponse:
    """Response model for get_event_status query in EventWorkflow.

    Contains metadata about the event's current state, including registered
    players and scheduled daily workflows.

    Attributes:
        event_id: Unique identifier for the event
        player_count: Total number of registered players
        daily_workflow_ids: Mapping of date strings to DailyWorkflow IDs

    Example:
        >>> response = EventStatusResponse(
        ...     event_id="marathon-trivia-2025",
        ...     player_count=150,
        ...     daily_workflow_ids={
        ...         "2025-03-10": "marathon-trivia-2025-2025-03-10",
        ...         "2025-03-11": "marathon-trivia-2025-2025-03-11",
        ...     }
        ... )
        >>> response.player_count
        150
    """

    event_id: str
    player_count: int
    daily_workflow_ids: dict[str, str]
