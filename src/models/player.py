# ABOUTME: Player data model representing player state and identity.
# Includes display name formatting and score tracking across multiple days.

from dataclasses import dataclass, field

from pydantic import EmailStr
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
@dataclass
class Player:
    """Player data model with email validation and score tracking.

    Represents a player's identity and state throughout a multi-day trivia event.
    Tracks total scores, daily scores, completed days, and current progress.

    Attributes:
        id: Unique player identifier (workflow ID)
        email: Player's email address (validated with EmailStr)
        first_name: Player's first name
        last_name: Player's last name
        company_name: Player's company name (optional, for CSV exports)
        total_score: Cumulative score across all days (default: 0)
        daily_scores: Map of date -> score for each completed day (default: {})
        completed_days: Set of dates for which player completed all questions (default: set())
        current_question_index: Map of date -> current question index (default: {})

    Example:
        >>> player = Player(
        ...     id="player123",
        ...     email="john.doe@example.com",
        ...     first_name="John",
        ...     last_name="Doe"
        ... )
        >>> player.get_display_name()
        'John D.'
        >>> player.total_score
        0
    """

    id: str
    email: EmailStr
    first_name: str
    last_name: str
    company_name: str | None = None
    total_score: int = 0
    daily_scores: dict[str, int] = field(default_factory=dict)
    completed_days: set[str] = field(default_factory=set)
    current_question_index: dict[str, int] = field(default_factory=dict)

    def get_display_name(self) -> str:
        """Return formatted display name in 'FirstName L.' format.

        If last_name is empty, returns just the first name.
        Otherwise, returns first name followed by last initial and period.

        Returns:
            Formatted display name string

        Example:
            >>> player = Player(id="1", email="j@ex.com", first_name="John", last_name="Doe")
            >>> player.get_display_name()
            'John D.'
            >>> player2 = Player(id="2", email="j@ex.com", first_name="Jane", last_name="")
            >>> player2.get_display_name()
            'Jane'
        """
        if self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.first_name
