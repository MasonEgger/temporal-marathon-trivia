# ABOUTME: Unit tests for the moderation activity.
# Tests verify player name moderation with mock client and edge cases.

import pytest
from temporalio.testing import ActivityEnvironment

from src.activities.moderation import ModerationActivities


class SimpleMockModerationClient:
    """Simple mock client for testing ModerationActivities."""

    def __init__(self, profane_words: list[str] | None = None) -> None:
        """Initialize with profanity word list.

        Args:
            profane_words: List of words to flag as profane.
        """
        if profane_words is None:
            profane_words = ["badword", "inappropriate", "profanity"]
        self._profane_words = [word.lower() for word in profane_words]

    async def check_name(self, name: str) -> bool:
        """Check if name contains profanity.

        Args:
            name: Player name to check

        Returns:
            True if profane, False if clean
        """
        name_lower = name.lower()
        for profane_word in self._profane_words:
            if profane_word in name_lower:
                return True
        return False


class TestModeratePlayerName:
    """Test suite for the moderate_player_name activity."""

    @pytest.mark.asyncio
    async def test_moderate_player_name_clean_name(self) -> None:
        """Test that clean names return False (not inappropriate)."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "Alice")

        assert result is False  # Clean name should not be flagged

    @pytest.mark.asyncio
    async def test_moderate_player_name_profane_name(self) -> None:
        """Test that profane names return True (inappropriate)."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "badword")

        assert result is True  # Profane name should be flagged

    @pytest.mark.asyncio
    async def test_moderate_player_name_empty_string(self) -> None:
        """Test moderation with empty string."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "")

        assert result is False  # Empty string should not be flagged

    @pytest.mark.asyncio
    async def test_moderate_player_name_special_characters(self) -> None:
        """Test moderation with special characters."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "Player_123!")

        assert result is False  # Special chars should be allowed

    @pytest.mark.asyncio
    async def test_moderate_player_name_numbers_only(self) -> None:
        """Test moderation with numbers only."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "12345")

        assert result is False  # Numbers should be allowed

    @pytest.mark.asyncio
    async def test_moderate_player_name_mixed_case(self) -> None:
        """Test moderation with mixed case profanity."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "BadWord")

        assert result is True  # Case variations should still be caught

    @pytest.mark.asyncio
    async def test_moderate_player_name_profanity_in_middle(self) -> None:
        """Test that profanity in middle of name is detected."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(
            activities.moderate_player_name, "AliceBadwordSmith"
        )

        assert result is True  # Profanity anywhere in name should be caught

    @pytest.mark.asyncio
    async def test_moderate_player_name_custom_profanity_list(self) -> None:
        """Test moderation with custom profanity list."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient(profane_words=["custom", "blocked"])
        activities = ModerationActivities(mock_client)

        # Should flag custom word
        result1 = await env.run(activities.moderate_player_name, "customuser")
        assert result1 is True

        # Should not flag default badword
        result2 = await env.run(activities.moderate_player_name, "badword")
        assert result2 is False

    @pytest.mark.asyncio
    async def test_moderate_player_name_whitespace_only(self) -> None:
        """Test moderation with whitespace only."""
        env = ActivityEnvironment()
        mock_client = SimpleMockModerationClient()
        activities = ModerationActivities(mock_client)

        result = await env.run(activities.moderate_player_name, "   ")

        assert result is False  # Whitespace only should be allowed
