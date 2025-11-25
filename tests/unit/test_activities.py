# ABOUTME: Unit tests for activity functions.
# Tests config loading, questions loading, email validation, S3 export logic.

from datetime import date, time
from pathlib import Path

import pytest
from pydantic import ValidationError
from temporalio.testing import ActivityEnvironment

from src.activities.config import ConfigActivities
from src.models.config import EventConfig


class TestConfigActivity:
    """Tests for ConfigActivities.load_event_config activity."""

    def test_load_event_config_successfully_parses_valid_toml_file(self) -> None:
        """Test that load_event_config() successfully parses valid TOML file."""
        config_path = "tests/fixtures/config.toml"

        # Run activity in test environment
        activity_env = ActivityEnvironment()
        activities = ConfigActivities()
        result = activity_env.run(activities.load_event_config, config_path)

        assert isinstance(result, EventConfig)

    def test_load_event_config_returns_event_config_instance_with_correct_values(
        self,
    ) -> None:
        """Test that load_event_config() returns EventConfig instance with correct values."""
        config_path = "tests/fixtures/config.toml"

        # Run activity in test environment
        activity_env = ActivityEnvironment()
        activities = ConfigActivities()
        result = activity_env.run(activities.load_event_config, config_path)

        # Verify dates
        assert result.start_date == date(2025, 3, 10)
        assert result.end_date == date(2025, 3, 12)
        assert result.day_start_time == time(9, 0, 0)
        assert result.day_end_time == time(17, 0, 0)
        assert result.timezone == "America/Los_Angeles"

        # Verify questions
        assert result.questions_file_path == "tests/fixtures/questions.json"
        assert result.questions_per_day == 5

        # Verify features
        assert result.show_correct_answer is True
        assert result.require_work_email is True

        # Verify S3
        assert result.s3_bucket_name == "test-marathon-trivia"
        assert result.s3_region == "us-west-2"

    def test_load_event_config_raises_file_not_found_error_for_missing_file(
        self,
    ) -> None:
        """Test that load_event_config() raises FileNotFoundError for missing file."""
        config_path = "tests/fixtures/nonexistent.toml"

        # Run activity in test environment
        activity_env = ActivityEnvironment()
        activities = ConfigActivities()

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            activity_env.run(activities.load_event_config, config_path)

    def test_load_event_config_raises_value_error_for_malformed_toml(self) -> None:
        """Test that load_event_config() raises ValueError for malformed TOML."""
        config_path = "tests/fixtures/config_malformed.toml"

        # Run activity in test environment
        activity_env = ActivityEnvironment()
        activities = ConfigActivities()

        with pytest.raises(ValueError, match="Failed to parse TOML"):
            activity_env.run(activities.load_event_config, config_path)

    def test_load_event_config_raises_value_error_for_missing_required_fields(
        self,
    ) -> None:
        """Test that load_event_config() raises ValueError for missing required fields."""
        config_path = "tests/fixtures/config_missing_fields.toml"

        # Run activity in test environment
        activity_env = ActivityEnvironment()
        activities = ConfigActivities()

        with pytest.raises(ValueError, match="Missing required section"):
            activity_env.run(activities.load_event_config, config_path)

    def test_load_event_config_validates_date_ranges(self) -> None:
        """Test that load_event_config() validates date ranges (end >= start)."""
        # Create a temporary config with invalid date range
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
start_date = "2025-03-12"
end_date = "2025-03-10"
day_start_time = "09:00:00"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            # Run activity in test environment
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValidationError, match="must be on or after"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            # Clean up temp file
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_missing_dates_section(self) -> None:
        """Test that missing [dates] section raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Missing required section.*dates"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_missing_features_section(
        self,
    ) -> None:
        """Test that missing [features] section raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
start_date = "2025-03-10"
end_date = "2025-03-12"
day_start_time = "09:00:00"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Missing required section.*features"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_missing_s3_section(self) -> None:
        """Test that missing [s3] section raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
start_date = "2025-03-10"
end_date = "2025-03-12"
day_start_time = "09:00:00"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Missing required section.*s3"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_invalid_date_format(self) -> None:
        """Test that invalid date format raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
start_date = "03/10/2025"
end_date = "2025-03-12"
day_start_time = "09:00:00"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Invalid date format.*YYYY-MM-DD"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_missing_date_field(self) -> None:
        """Test that missing start_date field raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
end_date = "2025-03-12"
day_start_time = "09:00:00"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Missing required date field"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_invalid_time_format(self) -> None:
        """Test that invalid time format raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
start_date = "2025-03-10"
end_date = "2025-03-12"
day_start_time = "9:00 AM"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Invalid time format.*HH:MM:SS"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_event_config_raises_error_for_missing_time_field(self) -> None:
        """Test that missing day_start_time field raises ValueError."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[dates]
start_date = "2025-03-10"
end_date = "2025-03-12"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "tests/fixtures/questions.json"
per_day = 5

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "test-marathon-trivia"
region = "us-west-2"
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = ConfigActivities()

            with pytest.raises(ValueError, match="Missing required time field"):
                activity_env.run(activities.load_event_config, temp_path)
        finally:
            Path(temp_path).unlink()
