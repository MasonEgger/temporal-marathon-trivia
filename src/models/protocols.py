# ABOUTME: Protocol definitions for API client interfaces.
# Defines contracts for moderation clients using Python's Protocol pattern.

from typing import Protocol


class ModerationProtocol(Protocol):
    """Protocol for moderation clients that check for inappropriate content.

    This protocol defines the interface for checking player names and other
    user-provided text for profanity or inappropriate content.
    """

    async def check_name(self, name: str) -> bool:
        """Check if a name contains profanity or inappropriate content.

        Args:
            name: Player name or text to check

        Returns:
            True if name contains profanity (should be rejected)
            False if name is clean (should be allowed)

        Raises:
            ValueError: If API response cannot be parsed
        """
        ...
