# ABOUTME: Moderation activity for validating player names.
# Uses injected moderation client to check names for profanity.

from temporalio import activity

from src.models.protocols import ModerationProtocol


class ModerationActivities:
    """Activity class for moderating player names.

    Uses an injected moderation client to check for profanity via external API.
    """

    def __init__(self, moderation_client: ModerationProtocol) -> None:
        """Initialize with moderation client.

        Args:
            moderation_client: Client for checking profanity
        """
        self.moderation_client = moderation_client

    @activity.defn(name="moderate_player_name")
    async def moderate_player_name(self, name: str) -> bool:
        """Check if a player name contains inappropriate content.

        Uses the injected moderation client (protocol-based) to validate player
        names against profanity filters. This prevents inappropriate names from
        being used in the game.

        Args:
            name: Player name to check

        Returns:
            True if name contains profanity (should be rejected)
            False if name is clean (should be allowed)

        Raises:
            ValueError: If moderation API response cannot be parsed
        """
        activity.logger.info(f"Moderating player name: '{name}'")

        is_profane = await self.moderation_client.check_name(name)

        if is_profane:
            activity.logger.warning(f"Player name '{name}' flagged as inappropriate")
        else:
            activity.logger.info(f"Player name '{name}' passed moderation")

        return is_profane
