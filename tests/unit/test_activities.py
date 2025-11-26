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


class TestQuestionsActivities:
    """Tests for QuestionsActivities (Step 6)."""

    def test_load_questions_successfully_parses_valid_json(self) -> None:
        """Test that load_questions() successfully parses valid JSON file."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/questions.json"

        activity_env = ActivityEnvironment()
        activities = QuestionsActivities()
        result = activity_env.run(activities.load_questions, questions_path)

        # Should return a dict
        assert isinstance(result, dict)
        # Should have 3 dates
        assert len(result) == 3
        assert "2025-03-10" in result
        assert "2025-03-11" in result
        assert "2025-03-12" in result

    def test_load_questions_returns_dict_of_date_to_questions(self) -> None:
        """Test that load_questions() returns dict[str, list[Question]]."""
        from src.activities.questions import QuestionsActivities
        from src.models.question import Question

        questions_path = "tests/fixtures/questions.json"

        activity_env = ActivityEnvironment()
        activities = QuestionsActivities()
        result = activity_env.run(activities.load_questions, questions_path)

        # Each date should map to a list of Questions
        for _date_key, questions in result.items():
            assert isinstance(questions, list)
            assert len(questions) == 5  # 5 questions per day in fixture
            for question in questions:
                assert isinstance(question, Question)

    def test_load_questions_validates_question_has_four_options(self) -> None:
        """Test that load_questions() validates each question has exactly 4 options (A, B, C, D)."""
        # This is validated by Question model's pydantic validation
        # We'll create a fixture with invalid options and verify it fails
        import tempfile

        from src.activities.questions import QuestionsActivities

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """
{
  "2025-03-10": [
    {
      "id": "q1",
      "text": "Test question?",
      "options": {
        "A": "Option A",
        "B": "Option B"
      },
      "correct_answer": "A"
    }
  ]
}
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = QuestionsActivities()

            with pytest.raises(ValueError, match="options must have exactly keys"):
                activity_env.run(activities.load_questions, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_questions_validates_correct_answer_is_abcd(self) -> None:
        """Test that load_questions() validates correct_answer is one of A/B/C/D."""
        import tempfile

        from src.activities.questions import QuestionsActivities

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """
{
  "2025-03-10": [
    {
      "id": "q1",
      "text": "Test question?",
      "options": {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      },
      "correct_answer": "E"
    }
  ]
}
"""
            )
            temp_path = f.name

        try:
            activity_env = ActivityEnvironment()
            activities = QuestionsActivities()

            with pytest.raises(ValueError, match="correct_answer must be one of"):
                activity_env.run(activities.load_questions, temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_questions_raises_filenotfounderror_for_missing_file(self) -> None:
        """Test that load_questions() raises FileNotFoundError for missing file."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/nonexistent.json"

        activity_env = ActivityEnvironment()
        activities = QuestionsActivities()

        with pytest.raises(FileNotFoundError, match="Questions file not found"):
            activity_env.run(activities.load_questions, questions_path)

    def test_load_questions_raises_valueerror_for_malformed_json(self) -> None:
        """Test that load_questions() raises ValueError for malformed JSON."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/questions_malformed.json"

        activity_env = ActivityEnvironment()
        activities = QuestionsActivities()

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            activity_env.run(activities.load_questions, questions_path)

    def test_get_questions_for_day_returns_correct_subset(self) -> None:
        """Test that get_questions_for_day() returns correct subset for a date."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/questions.json"

        activity_env = ActivityEnvironment()
        activities = QuestionsActivities()
        result = activity_env.run(activities.get_questions_for_day, questions_path, "2025-03-10")

        # Should return list of 5 questions for day 1
        assert isinstance(result, list)
        assert len(result) == 5
        # Verify first question ID
        assert result[0].id == "day1_q1"

    def test_get_questions_for_day_raises_keyerror_for_invalid_date(self) -> None:
        """Test that get_questions_for_day() raises KeyError for invalid date."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/questions.json"

        activity_env = ActivityEnvironment()
        activities = QuestionsActivities()

        with pytest.raises(KeyError, match="Date.*not found in questions file"):
            activity_env.run(activities.get_questions_for_day, questions_path, "2025-03-99")

    def test_validate_questions_file_succeeds_for_valid_file(self) -> None:
        """Test that validate_questions_file() succeeds for valid file."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/questions.json"
        config_path = "tests/fixtures/config.toml"

        # Load config first
        from src.activities.config import ConfigActivities

        activity_env = ActivityEnvironment()
        config_activities = ConfigActivities()
        config = activity_env.run(config_activities.load_event_config, config_path)

        # Validate questions file
        activities = QuestionsActivities()
        # Should not raise any exception
        activity_env.run(activities.validate_questions_file, questions_path, config)

    def test_validate_questions_file_validates_dates_match_config(self) -> None:
        """Test that validate_questions_file() raises ValueError if dates don't match config."""
        # Create questions file with dates that don't match config
        import tempfile

        from src.activities.questions import QuestionsActivities

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """
{
  "2025-03-10": [
    {
      "id": "q1",
      "text": "Q?",
      "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
      "correct_answer": "A"
    }
  ]
}
"""
            )
            temp_path = f.name

        try:
            config_path = "tests/fixtures/config.toml"

            from src.activities.config import ConfigActivities

            activity_env = ActivityEnvironment()
            config_activities = ConfigActivities()
            config = activity_env.run(config_activities.load_event_config, config_path)

            activities = QuestionsActivities()

            with pytest.raises(ValueError, match="Missing questions for date"):
                activity_env.run(activities.validate_questions_file, temp_path, config)
        finally:
            Path(temp_path).unlink()

    def test_validate_questions_file_validates_question_count_per_day(self) -> None:
        """Test that validate_questions_file() raises ValueError if question count doesn't match."""
        # Create questions file with wrong number of questions per day
        import tempfile

        from src.activities.questions import QuestionsActivities

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """
{
  "2025-03-10": [
    {
      "id": "q1",
      "text": "Q?",
      "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
      "correct_answer": "A"
    },
    {
      "id": "q2",
      "text": "Q?",
      "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
      "correct_answer": "A"
    }
  ],
  "2025-03-11": [
    {
      "id": "q1",
      "text": "Q?",
      "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
      "correct_answer": "A"
    }
  ],
  "2025-03-12": [
    {
      "id": "q1",
      "text": "Q?",
      "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
      "correct_answer": "A"
    }
  ]
}
"""
            )
            temp_path = f.name

        try:
            config_path = "tests/fixtures/config.toml"

            from src.activities.config import ConfigActivities

            activity_env = ActivityEnvironment()
            config_activities = ConfigActivities()
            config = activity_env.run(config_activities.load_event_config, config_path)

            activities = QuestionsActivities()

            with pytest.raises(ValueError, match="Date.*has.*questions, expected"):
                activity_env.run(activities.validate_questions_file, temp_path, config)
        finally:
            Path(temp_path).unlink()

    def test_validate_questions_file_raises_filenotfounderror_for_missing_file(
        self,
    ) -> None:
        """Test that validate_questions_file() raises FileNotFoundError for missing file."""
        from src.activities.questions import QuestionsActivities

        questions_path = "tests/fixtures/nonexistent.json"
        config_path = "tests/fixtures/config.toml"

        from src.activities.config import ConfigActivities

        activity_env = ActivityEnvironment()
        config_activities = ConfigActivities()
        config = activity_env.run(config_activities.load_event_config, config_path)

        activities = QuestionsActivities()

        with pytest.raises(FileNotFoundError):
            activity_env.run(activities.validate_questions_file, questions_path, config)


class TestEmailActivities:
    """Tests for EmailActivities (Step 7)."""

    def test_validate_email_returns_true_for_valid_work_email(self) -> None:
        """Test that validate_email() returns True for valid work email."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "john.doe@company.com", True)

        assert result is True

    def test_validate_email_returns_true_for_any_email_when_require_work_email_false(
        self,
    ) -> None:
        """Test that validate_email() returns True for any email when require_work_email=False."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()

        # Gmail should be valid when not requiring work email
        result = activity_env.run(activities.validate_email, "user@gmail.com", False)
        assert result is True

    def test_validate_email_returns_false_for_invalid_email_format(self) -> None:
        """Test that validate_email() returns False for invalid email format (no @)."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "not-an-email", True)

        assert result is False

    def test_validate_email_returns_false_for_gmail_when_require_work_email_true(
        self,
    ) -> None:
        """Test that validate_email() returns False for gmail.com when require_work_email=True."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "user@gmail.com", True)

        assert result is False

    def test_validate_email_returns_false_for_yahoo_when_require_work_email_true(
        self,
    ) -> None:
        """Test that validate_email() returns False for yahoo.com when require_work_email=True."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "user@yahoo.com", True)

        assert result is False

    def test_validate_email_returns_false_for_hotmail_when_require_work_email_true(
        self,
    ) -> None:
        """Test that validate_email() returns False for hotmail.com when require_work_email=True."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "user@hotmail.com", True)

        assert result is False

    def test_validate_email_returns_false_for_outlook_when_require_work_email_true(
        self,
    ) -> None:
        """Test that validate_email() returns False for outlook.com when require_work_email=True."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "user@outlook.com", True)

        assert result is False

    def test_validate_email_returns_false_for_aol_when_require_work_email_true(
        self,
    ) -> None:
        """Test that validate_email() returns False for aol.com when require_work_email=True."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "user@aol.com", True)

        assert result is False

    def test_validate_email_returns_false_for_icloud_when_require_work_email_true(
        self,
    ) -> None:
        """Test that validate_email() returns False for icloud.com when require_work_email=True."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "user@icloud.com", True)

        assert result is False

    def test_validate_email_handles_empty_string_gracefully(self) -> None:
        """Test that validate_email() handles empty string gracefully (returns False)."""
        from src.activities.email import EmailActivities

        activity_env = ActivityEnvironment()
        activities = EmailActivities()
        result = activity_env.run(activities.validate_email, "", True)

        assert result is False


class TestExportActivities:
    """Tests for ExportActivities (Step 8)."""

    def test_export_daily_csv_to_s3_creates_csv_with_correct_format(self) -> None:
        """Test that export_daily_csv_to_s3() creates CSV with correct format."""
        from moto import mock_aws

        from src.activities.export import ExportActivities
        from tests.fixtures.players import create_test_players

        # Use moto to mock S3
        with mock_aws():
            import boto3

            # Create mock S3 bucket
            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            # Get test players
            players = create_test_players()

            # Run activity
            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            result = activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                players,
                ["2025-03-10", "2025-03-11", "2025-03-12"],
            )

            # Verify S3 URL is returned
            assert isinstance(result, str)
            assert "marathon-trivia-2025-03-12.csv" in result

            # Get CSV from S3
            response = s3_client.get_object(Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv")
            csv_content = response["Body"].read().decode("utf-8")

            # Verify CSV format (has header and 3 data rows)
            lines = csv_content.strip().split("\n")
            assert len(lines) == 4  # 1 header + 3 players

    def test_export_daily_csv_to_s3_includes_all_players(self) -> None:
        """Test that CSV includes all players."""
        from moto import mock_aws

        from src.activities.export import ExportActivities
        from tests.fixtures.players import create_test_players

        with mock_aws():
            import boto3

            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            players = create_test_players()

            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                players,
                ["2025-03-10", "2025-03-11", "2025-03-12"],
            )

            # Get CSV from S3
            response = s3_client.get_object(Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv")
            csv_content = response["Body"].read().decode("utf-8")

            # Verify all 3 players are in CSV
            assert "john.doe@example.com" in csv_content
            assert "alice.smith@example.com" in csv_content
            assert "bob.adams@example.com" in csv_content

    def test_export_daily_csv_to_s3_has_correct_columns(self) -> None:
        """Test that CSV columns match spec.

        Columns: email, first_name, last_name, total_score, dayN_score, completed_days.
        """
        from moto import mock_aws

        from src.activities.export import ExportActivities
        from tests.fixtures.players import create_test_players

        with mock_aws():
            import boto3

            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            players = create_test_players()

            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                players,
                ["2025-03-10", "2025-03-11", "2025-03-12"],
            )

            # Get CSV from S3
            response = s3_client.get_object(Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv")
            csv_content = response["Body"].read().decode("utf-8")

            # Verify header row has correct columns
            header = csv_content.split("\n")[0]
            assert "email" in header
            assert "first_name" in header
            assert "last_name" in header
            assert "total_score" in header
            assert "day1_score" in header
            assert "day2_score" in header
            assert "day3_score" in header
            assert "completed_days" in header

    def test_export_daily_csv_to_s3_has_dynamic_day_columns(self) -> None:
        """Test that CSV day columns are dynamic based on event dates."""
        from moto import mock_aws

        from src.activities.export import ExportActivities
        from tests.fixtures.players import create_test_players

        with mock_aws():
            import boto3

            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            players = create_test_players()

            # Test with 2 days only
            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                players,
                ["2025-03-10", "2025-03-11"],  # Only 2 days
            )

            # Get CSV from S3
            response = s3_client.get_object(Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv")
            csv_content = response["Body"].read().decode("utf-8")

            # Verify header row has only 2 day columns
            header = csv_content.split("\n")[0]
            assert "day1_score" in header
            assert "day2_score" in header
            assert "day3_score" not in header  # Should not exist

    def test_export_daily_csv_to_s3_uploads_to_s3_with_correct_key(self) -> None:
        """Test that export_daily_csv_to_s3() uploads to S3 with correct key format.

        Key format: marathon-trivia-{date}.csv
        """
        from moto import mock_aws

        from src.activities.export import ExportActivities
        from tests.fixtures.players import create_test_players

        with mock_aws():
            import boto3

            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            players = create_test_players()

            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                players,
                ["2025-03-10", "2025-03-11", "2025-03-12"],
            )

            # Verify object exists with correct key
            response = s3_client.head_object(Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv")
            assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_export_daily_csv_to_s3_returns_s3_url(self) -> None:
        """Test that export_daily_csv_to_s3() returns S3 URL."""
        from moto import mock_aws

        from src.activities.export import ExportActivities
        from tests.fixtures.players import create_test_players

        with mock_aws():
            import boto3

            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            players = create_test_players()

            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            result = activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                players,
                ["2025-03-10", "2025-03-11", "2025-03-12"],
            )

            # Verify S3 URL format
            expected_url = "https://test-bucket.s3.us-west-2.amazonaws.com/marathon-trivia-2025-03-12.csv"
            assert result == expected_url

    def test_export_daily_csv_to_s3_handles_empty_player_list(self) -> None:
        """Test that export_daily_csv_to_s3() handles empty player list gracefully."""
        from moto import mock_aws

        from src.activities.export import ExportActivities

        with mock_aws():
            import boto3

            s3_client = boto3.client("s3", region_name="us-west-2")
            bucket_name = "test-bucket"
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

            activity_env = ActivityEnvironment()
            activities = ExportActivities()
            result = activity_env.run(
                activities.export_daily_csv_to_s3,
                bucket_name,
                "us-west-2",
                "2025-03-12",
                [],  # Empty player list
                ["2025-03-10", "2025-03-11", "2025-03-12"],
            )

            # Should return S3 URL
            assert isinstance(result, str)
            assert "marathon-trivia-2025-03-12.csv" in result

            # Get CSV from S3
            response = s3_client.get_object(Bucket=bucket_name, Key="marathon-trivia-2025-03-12.csv")
            csv_content = response["Body"].read().decode("utf-8")

            # Should have header only
            lines = csv_content.strip().split("\n")
            assert len(lines) == 1  # Just header, no data rows
