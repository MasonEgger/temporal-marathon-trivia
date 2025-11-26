# ABOUTME: Workflow state models for PlayerEntityWorkflow, DailyWorkflow, and EventWorkflow.
# Encapsulates all state needed by workflows for state management and persistence.

from dataclasses import dataclass, field

from src.models.config import EventConfig
from src.models.player import Player
from src.models.question import Question


@dataclass
class PlayerState:
    """State maintained by PlayerEntityWorkflow for a single player.

    This dataclass encapsulates the workflow state including the Player model
    and additional workflow-specific fields for tracking current progress.

    Attributes:
        player: Player model instance with identity and score tracking
        current_day: Current day being played (None if no day started)
        current_question_index: Index of current question in current day (0-based)
        current_questions: List of questions for the current day (None if no day started)

    Example:
        >>> player = Player(id="p1", email="a@ex.com", first_name="Alice", last_name="Smith")
        >>> state = PlayerState(player=player, current_day="2025-03-10", current_question_index=0)
        >>> state.current_day
        '2025-03-10'
    """

    player: Player
    current_day: str | None = None
    current_question_index: int = 0
    current_questions: list[Question] | None = None


@dataclass
class DailyState:
    """State for DailyWorkflow managing a single day's trivia session.

    This dataclass encapsulates all state needed by DailyWorkflow to manage
    a single day's trivia session, including questions, player scores, and
    event configuration.

    Attributes:
        date: The date of this daily session (ISO format string, e.g., "2025-03-10").
        questions: List of Question objects for this day.
        player_scores: Mapping of player_id to their score for this day.
        completed_players: Set of player_ids who have completed this day.
        player_info: Mapping of player_id to tuple of (email, first_name, last_name).
        config: Event configuration with timing and settings.

    Example:
        >>> from datetime import date, time
        >>> config = EventConfig(
        ...     start_date=date(2025, 3, 10),
        ...     end_date=date(2025, 3, 12),
        ...     day_start_time=time(9, 0),
        ...     day_end_time=time(17, 0),
        ...     timezone="America/Los_Angeles",
        ...     questions_file_path="config/questions.json",
        ...     questions_per_day=5,
        ...     show_correct_answer=True,
        ...     require_work_email=False,
        ...     s3_bucket_name="test-bucket",
        ...     s3_region="us-west-2"
        ... )
        >>> questions = [Question(...), Question(...)]
        >>> state = DailyState(
        ...     date="2025-03-10",
        ...     questions=questions,
        ...     config=config
        ... )
        >>> state.player_scores
        {}
        >>> state.completed_players
        set()
    """

    date: str
    questions: list[Question]
    player_scores: dict[str, int] = field(default_factory=dict)
    completed_players: set[str] = field(default_factory=set)
    player_info: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    config: EventConfig | None = None


@dataclass
class EventState:
    """State for EventWorkflow managing the entire event lifecycle.

    This dataclass encapsulates all state needed by EventWorkflow to manage
    the entire event, including configuration, player registry, and tracking
    of daily child workflows.

    Attributes:
        event_id: Unique identifier for this event.
        config: Event configuration loaded from TOML file.
        daily_workflow_ids: Mapping of date strings to DailyWorkflow workflow IDs.
        player_count: Total number of registered players.
        player_registry: Mapping of email to player_id for duplicate detection.

    Example:
        >>> from datetime import date, time
        >>> config = EventConfig(
        ...     start_date=date(2025, 3, 10),
        ...     end_date=date(2025, 3, 12),
        ...     day_start_time=time(9, 0),
        ...     day_end_time=time(17, 0),
        ...     timezone="America/Los_Angeles",
        ...     questions_file_path="config/questions.json",
        ...     questions_per_day=5,
        ...     show_correct_answer=True,
        ...     require_work_email=False,
        ...     s3_bucket_name="test-bucket",
        ...     s3_region="us-west-2"
        ... )
        >>> state = EventState(event_id="my-event", config=config)
        >>> state.player_count
        0
        >>> state.player_registry
        {}
    """

    event_id: str
    config: EventConfig
    daily_workflow_ids: dict[str, str] = field(default_factory=dict)
    player_count: int = 0
    player_registry: dict[str, str] = field(default_factory=dict)
