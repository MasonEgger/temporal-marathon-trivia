# ABOUTME: Configuration loading activities for event setup.
# Loads and validates TOML configuration files for trivia events.

import tomllib
from datetime import date, time
from pathlib import Path

from temporalio import activity

from src.models.config import EventConfig
from src.models.ux_config import UXConfig


class ConfigActivities:
    """Activity class for configuration-related operations."""

    @activity.defn
    def load_event_config(self, config_path: str) -> EventConfig:
        """Load and parse event configuration from TOML file.

        Reads a TOML configuration file, extracts all required sections,
        parses date/time strings, and creates an EventConfig instance.
        Pydantic validation handles field validation automatically.

        Args:
            config_path: Path to the TOML configuration file

        Returns:
            EventConfig: Validated event configuration instance

        Raises:
            FileNotFoundError: If the configuration file does not exist
            ValueError: If the TOML file is malformed or cannot be parsed
            ValidationError: If required fields are missing or validation fails

        Example:
            >>> activities = ConfigActivities()
            >>> config = activities.load_event_config("config/event.toml")
            >>> print(config.start_date)
            2025-03-10
        """
        # Check if file exists
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Read and parse TOML file
        try:
            with open(config_file, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Failed to parse TOML configuration file: {e}") from e
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {e}") from e

        # Extract sections - provide helpful error messages for missing sections
        try:
            dates_section = data["dates"]
        except KeyError as e:
            raise ValueError("Missing required section '[dates]' in configuration file") from e

        try:
            questions_section = data["questions"]
        except KeyError as e:
            raise ValueError("Missing required section '[questions]' in configuration file") from e

        try:
            features_section = data["features"]
        except KeyError as e:
            raise ValueError("Missing required section '[features]' in configuration file") from e

        try:
            s3_section = data["s3"]
        except KeyError as e:
            raise ValueError("Missing required section '[s3]' in configuration file") from e

        # Parse date strings to date objects (ISO format: YYYY-MM-DD)
        try:
            start_date = date.fromisoformat(dates_section["start_date"])
            end_date = date.fromisoformat(dates_section["end_date"])
        except KeyError as e:
            raise ValueError(f"Missing required date field in [dates] section: {e}") from e
        except ValueError as e:
            raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {e}") from e

        # Parse time strings to time objects (ISO format: HH:MM:SS)
        try:
            day_start_time = time.fromisoformat(dates_section["day_start_time"])
            day_end_time = time.fromisoformat(dates_section["day_end_time"])
        except KeyError as e:
            raise ValueError(f"Missing required time field in [dates] section: {e}") from e
        except ValueError as e:
            raise ValueError(f"Invalid time format (expected HH:MM:SS): {e}") from e

        # Create and return EventConfig instance
        # Pydantic validation will handle field validation
        return EventConfig(
            start_date=start_date,
            end_date=end_date,
            day_start_time=day_start_time,
            day_end_time=day_end_time,
            timezone=dates_section["timezone"],
            questions_file_path=questions_section["file_path"],
            questions_per_day=questions_section["per_day"],
            show_correct_answer=features_section["show_correct_answer"],
            require_work_email=features_section["require_work_email"],
            require_company_name=features_section["require_company_name"],
            s3_bucket_name=s3_section["bucket_name"],
            s3_region=s3_section["region"],
        )

    @activity.defn
    def load_ux_config(self, config_path: str) -> UXConfig:
        """Load and parse UX configuration from TOML file.

        Reads a TOML configuration file and extracts UI/presentation fields
        including branding, colors, and user-facing messages.

        Args:
            config_path: Path to the TOML configuration file

        Returns:
            UXConfig: UX configuration instance with branding and UI settings

        Raises:
            FileNotFoundError: If the configuration file does not exist
            ValueError: If the TOML file is malformed or required sections are missing

        Example:
            >>> activities = ConfigActivities()
            >>> ux_config = activities.load_ux_config("config/event.toml")
            >>> print(ux_config.title)
            AWS re:Invent 2025 Trivia
        """
        # Check if file exists
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Read and parse TOML file
        try:
            with open(config_file, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"Failed to parse TOML configuration file: {e}") from e
        except Exception as e:
            raise ValueError(f"Error reading configuration file: {e}") from e

        # Extract sections - provide helpful error messages for missing sections
        try:
            ui_branding_section = data["ui"]["branding"]
        except KeyError as e:
            raise ValueError("Missing required section '[ui.branding]' in configuration file") from e

        try:
            ui_messages_section = data["ui"]["messages"]
        except KeyError as e:
            raise ValueError("Missing required section '[ui.messages]' in configuration file") from e

        try:
            ui_colors_section = data["ui"]["colors"]
        except KeyError as e:
            raise ValueError("Missing required section '[ui.colors]' in configuration file") from e

        try:
            ui_performance_section = data["ui"]["performance"]
        except KeyError as e:
            raise ValueError("Missing required section '[ui.performance]' in configuration file") from e

        # Create and return UXConfig instance
        return UXConfig(
            title=ui_branding_section["title"],
            description=ui_branding_section["description"],
            base_url=ui_branding_section["base_url"],
            welcome_message=ui_branding_section["welcome_message"],
            completion_message=ui_messages_section["completion_message"],
            day_over_message=ui_messages_section["day_over_message"],
            not_started_message=ui_messages_section["not_started_message"],
            already_completed_message=ui_messages_section["already_completed_message"],
            invalid_work_email_message=ui_messages_section["invalid_work_email_message"],
            primary_color=ui_colors_section["primary_color"],
            secondary_color=ui_colors_section["secondary_color"],
            background_color=ui_colors_section["background_color"],
            text_color=ui_colors_section["text_color"],
            leaderboard_refresh_seconds=ui_performance_section["leaderboard_refresh_seconds"],
        )
