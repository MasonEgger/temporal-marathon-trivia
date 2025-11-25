# ABOUTME: Leaderboard entry model for displaying player rankings.
# Used for leaderboard display and 'find my rank' functionality.

from dataclasses import dataclass

from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
@dataclass
class LeaderboardEntry:
    """Leaderboard entry model representing a player's rank and scores.

    This model is used for displaying leaderboards and enabling the 'find my rank'
    functionality. It aggregates a player's performance across all days of the event.

    Attributes:
        rank: The player's rank on the leaderboard (1 = first place).
        display_name: The player's display name in 'FirstName L.' format.
        total_score: The player's cumulative score across all days.
        daily_scores: A dictionary mapping date strings (YYYY-MM-DD) to daily scores.
        email: The player's email address (for identification).

    Example:
        >>> entry = LeaderboardEntry(
        ...     rank=1,
        ...     display_name="John D.",
        ...     total_score=150,
        ...     daily_scores={"2025-03-10": 50, "2025-03-11": 100},
        ...     email="john.doe@example.com"
        ... )
        >>> entry.rank
        1
        >>> entry.total_score
        150
    """

    rank: int
    display_name: str
    total_score: int
    daily_scores: dict[str, int]
    email: str
