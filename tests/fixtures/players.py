# ABOUTME: Test fixtures for creating Player instances in tests.
# Provides factory functions for single and multiple players with varying scores.

from src.models.player import Player


def create_test_player(
    player_id: str = "test-player-1",
    email: str = "john.doe@example.com",
    first_name: str = "John",
    last_name: str = "Doe",
    total_score: int = 0,
    daily_scores: dict[str, int] | None = None,
    completed_days: set[str] | None = None,
) -> Player:
    """Create a single test Player instance with customizable fields.

    Args:
        player_id: Player ID (default: "test-player-1")
        email: Player email (default: "john.doe@example.com")
        first_name: Player first name (default: "John")
        last_name: Player last name (default: "Doe")
        total_score: Total score across all days (default: 0)
        daily_scores: Daily scores dict (default: empty dict)
        completed_days: Set of completed day dates (default: empty set)

    Returns:
        Player instance with specified fields.
    """
    return Player(
        id=player_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        total_score=total_score,
        daily_scores=daily_scores or {},
        completed_days=completed_days or set(),
    )


def create_test_players() -> list[Player]:
    """Create a list of 3 test players with different scores for testing.

    Returns:
        List of 3 Player instances with varying scores and completion status.
            - Player 1: John Doe, 8 total (day1: 3, day2: 5), completed 2 days
            - Player 2: Alice Smith, 12 total (day1: 5, day2: 4, day3: 3), completed 3 days
            - Player 3: Bob Adams, 5 total (day1: 5), completed 1 day
    """
    player1 = Player(
        id="player-1",
        email="john.doe@example.com",
        first_name="John",
        last_name="Doe",
        total_score=8,
        daily_scores={"2025-03-10": 3, "2025-03-11": 5},
        completed_days={"2025-03-10", "2025-03-11"},
    )

    player2 = Player(
        id="player-2",
        email="alice.smith@example.com",
        first_name="Alice",
        last_name="Smith",
        total_score=12,
        daily_scores={"2025-03-10": 5, "2025-03-11": 4, "2025-03-12": 3},
        completed_days={"2025-03-10", "2025-03-11", "2025-03-12"},
    )

    player3 = Player(
        id="player-3",
        email="bob.adams@example.com",
        first_name="Bob",
        last_name="Adams",
        total_score=5,
        daily_scores={"2025-03-10": 5},
        completed_days={"2025-03-10"},
    )

    return [player1, player2, player3]
