# ABOUTME: Event configuration model loaded from TOML files.
# Validates dates, times, and feature flags for trivia events (workflow-essential fields only).

from dataclasses import dataclass
from datetime import date, time
from zoneinfo import ZoneInfo

from pydantic import model_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
@dataclass
class EventConfig:
    """Event configuration model for workflow-essential settings.

    This model contains only the fields required by Temporal workflows.
    API/UI-specific fields (title, description, colors, messages) will be added
    in Phase 4 when implementing the API layer.

    Attributes:
        start_date: First day of the event (inclusive).
        end_date: Last day of the event (inclusive).
        day_start_time: Time when daily questions become available.
        day_end_time: Time when daily questions close.
        timezone: IANA timezone string (e.g., "America/Los_Angeles").
        questions_file_path: Path to JSON file containing questions.
        questions_per_day: Number of questions per day (must be positive).
        show_correct_answer: Whether to show correct answer after submission.
        require_work_email: Whether to block consumer email domains.
        s3_bucket_name: S3 bucket for CSV exports.
        s3_region: AWS region for S3 bucket.

    Validation Rules:
        - end_date must be after start_date
        - timezone must be a valid IANA timezone
        - questions_per_day must be positive (> 0)

    Example:
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
        ...     s3_bucket_name="trivia-exports",
        ...     s3_region="us-west-2"
        ... )
        >>> config.questions_per_day
        5
    """

    start_date: date
    end_date: date
    day_start_time: time
    day_end_time: time
    timezone: str
    questions_file_path: str
    questions_per_day: int
    show_correct_answer: bool
    require_work_email: bool
    s3_bucket_name: str
    s3_region: str

    @model_validator(mode="after")
    def validate_dates(self) -> EventConfig:
        """Validate that end_date is on or after start_date."""
        if self.end_date < self.start_date:
            raise ValueError(f"end_date ({self.end_date}) must be on or after start_date ({self.start_date})")
        return self

    @model_validator(mode="after")
    def validate_timezone(self) -> EventConfig:
        """Validate that timezone is a valid IANA timezone string."""
        try:
            ZoneInfo(self.timezone)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{self.timezone}': {e}") from e
        return self

    @model_validator(mode="after")
    def validate_questions_per_day(self) -> EventConfig:
        """Validate that questions_per_day is positive."""
        if self.questions_per_day <= 0:
            raise ValueError(f"questions_per_day must be positive, got {self.questions_per_day}")
        return self

    def get_all_dates(self) -> list[date]:
        """Return list of all dates from start_date to end_date (inclusive).

        Returns:
            A list of date objects representing each day of the event.

        Example:
            >>> config = EventConfig(
            ...     start_date=date(2025, 3, 10),
            ...     end_date=date(2025, 3, 12),
            ...     ...
            ... )
            >>> config.get_all_dates()
            [date(2025, 3, 10), date(2025, 3, 11), date(2025, 3, 12)]
        """
        from datetime import timedelta

        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates
