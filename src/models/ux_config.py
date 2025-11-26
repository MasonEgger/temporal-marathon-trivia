# ABOUTME: UX configuration model for UI/presentation settings.
# Contains branding, colors, and user-facing messages loaded from TOML files.

from dataclasses import dataclass

from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
@dataclass
class UXConfig:
    """UX configuration model for UI/presentation settings.

    This model contains fields for branding, colors, and user-facing messages.
    Separate from EventConfig to maintain separation between business logic
    and presentation concerns.

    Attributes:
        title: Event title displayed on landing page.
        description: Event description/tagline.
        base_url: Base URL for the application.
        completion_message: Message shown when player completes a day.
        day_over_message: Message shown when day has ended.
        not_started_message: Message shown when day hasn't started yet.
        already_completed_message: Message shown when player already completed day.
        invalid_work_email_message: Message shown when work email is required but consumer email provided.
        primary_color: Primary color (hex format, e.g., "#3b82f6").
        secondary_color: Secondary color (hex format).
        background_color: Background color (hex format).
        text_color: Text color (hex format).
        leaderboard_refresh_seconds: How often to refresh leaderboard (default: 30).

    Example:
        >>> ux_config = UXConfig(
        ...     title="AWS re:Invent 2025 Trivia",
        ...     description="Test your cloud knowledge!",
        ...     base_url="trivia.ziggy.codes",
        ...     completion_message="Great job! Check the leaderboard.",
        ...     day_over_message="Today's questions have closed.",
        ...     not_started_message="Questions not available yet.",
        ...     already_completed_message="You've already completed today.",
        ...     primary_color="#3b82f6",
        ...     secondary_color="#8b5cf6",
        ...     background_color="#ffffff",
        ...     text_color="#1f2937",
        ...     leaderboard_refresh_seconds=30
        ... )
        >>> ux_config.title
        'AWS re:Invent 2025 Trivia'
    """

    title: str
    description: str
    base_url: str
    completion_message: str
    day_over_message: str
    not_started_message: str
    already_completed_message: str
    invalid_work_email_message: str
    primary_color: str
    secondary_color: str
    background_color: str
    text_color: str
    leaderboard_refresh_seconds: int = 30
