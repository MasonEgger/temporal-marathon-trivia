# ABOUTME: PurgoMalum moderation client implementation.
# Checks player names for profanity using PurgoMalum free API.

from urllib.parse import quote_plus

import httpx


def parse_profanity_response(response: str) -> bool:
    """Parse PurgoMalum API boolean string response to Python bool.

    Args:
        response: String response from API ("true" or "false")

    Returns:
        True if profanity detected, False if clean

    Raises:
        ValueError: If response is not "true" or "false"
    """
    cleaned = response.strip().lower()
    if cleaned == "true":
        return True
    elif cleaned == "false":
        return False
    else:
        raise ValueError(f"Invalid profanity response: {response}")


def build_moderation_url(base_url: str, name: str) -> str:
    """Build PurgoMalum API URL with properly encoded name parameter.

    Args:
        base_url: Base API URL (e.g., https://www.purgomalum.com/service/containsprofanity)
        name: Player name to check

    Returns:
        Complete API URL with encoded text parameter
    """
    encoded_name = quote_plus(name)
    return f"{base_url}?text={encoded_name}"


class PurgoMalumClient:
    """Client for PurgoMalum profanity detection API.

    Uses the free PurgoMalum service to check if text contains profanity.
    No API key required.
    """

    def __init__(
        self, base_url: str = "https://www.purgomalum.com/service/containsprofanity"
    ) -> None:
        """Initialize PurgoMalum client.

        Args:
            base_url: Base URL for PurgoMalum API endpoint
        """
        self.base_url = base_url

    async def check_name(self, name: str) -> bool:
        """Check if a player name contains profanity.

        Args:
            name: Player name to check

        Returns:
            True if name contains profanity (should be rejected)
            False if name is clean (should be allowed)

        Raises:
            ValueError: If API response cannot be parsed
            httpx.HTTPError: If API request fails
        """
        url = build_moderation_url(self.base_url, name)

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            # PurgoMalum returns plain text "true" or "false"
            response_text = response.text
            return parse_profanity_response(response_text)
