# ABOUTME: Question loading activities for retrieving trivia questions.
# Loads and validates JSON question files with A/B/C/D answer format.

import json
from pathlib import Path

from temporalio import activity

from src.models.config import EventConfig
from src.models.question import Question


class QuestionsActivities:
    """Activity class for question-related operations."""

    @activity.defn
    def load_questions(self, file_path: str) -> dict[str, list[Question]]:
        """Load and parse questions from JSON file.

        Reads a JSON file containing trivia questions organized by date keys.
        Each question is validated using the Question model's pydantic validation.

        Args:
            file_path: Path to the JSON questions file

        Returns:
            Dict mapping date strings (YYYY-MM-DD) to lists of Question objects

        Raises:
            FileNotFoundError: If the questions file doesn't exist
            ValueError: If JSON is malformed or questions fail validation

        Example:
            >>> activities = QuestionsActivities()
            >>> questions = activities.load_questions("config/questions.json")
            >>> questions["2025-03-10"]  # Returns list[Question] for that date
        """
        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Questions file not found: {file_path}. "
                "Please verify the file path is correct."
            )

        # Read and parse JSON
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON file '{file_path}': {e}. "
                "Ensure the file contains valid JSON."
            ) from e

        # Convert each question dict to Question object
        # Pydantic validation will handle A/B/C/D and correct_answer validation
        result: dict[str, list[Question]] = {}
        try:
            for date_key, question_dicts in data.items():
                questions = [Question(**q) for q in question_dicts]
                result[date_key] = questions
        except Exception as e:
            raise ValueError(
                f"Failed to validate question data in '{file_path}': {e}"
            ) from e

        return result

    @activity.defn
    def get_questions_for_day(self, file_path: str, date: str) -> list[Question]:
        """Get questions for a specific date.

        Args:
            file_path: Path to the JSON questions file
            date: Date string in YYYY-MM-DD format

        Returns:
            List of Question objects for the specified date

        Raises:
            FileNotFoundError: If the questions file doesn't exist
            ValueError: If JSON is malformed or questions fail validation
            KeyError: If the date is not found in the questions file

        Example:
            >>> activities = QuestionsActivities()
            >>> questions = activities.get_questions_for_day(
            ...     "config/questions.json", "2025-03-10"
            ... )
            >>> len(questions)  # Number of questions for that day
        """
        # Load all questions
        all_questions = self.load_questions(file_path)

        # Get questions for specific date
        if date not in all_questions:
            raise KeyError(
                f"Date '{date}' not found in questions file. "
                f"Available dates: {', '.join(sorted(all_questions.keys()))}"
            )

        return all_questions[date]

    @activity.defn
    def validate_questions_file(
        self, file_path: str, config: EventConfig
    ) -> None:
        """Validate questions file against event configuration.

        Ensures that:
        - All expected dates from config have questions
        - Each date has the correct number of questions
        - All questions pass validation (via load_questions)

        Args:
            file_path: Path to the JSON questions file
            config: EventConfig with expected dates and questions_per_day

        Raises:
            FileNotFoundError: If the questions file doesn't exist
            ValueError: If validation fails

        Example:
            >>> activities = QuestionsActivities()
            >>> config = EventConfig(...)
            >>> activities.validate_questions_file("config/questions.json", config)
            # Raises ValueError if validation fails, otherwise returns None
        """
        # Load all questions (will raise FileNotFoundError or ValueError if issues)
        all_questions = self.load_questions(file_path)

        # Get expected dates from config
        expected_dates = config.get_all_dates()
        expected_dates_str = [d.isoformat() for d in expected_dates]

        # Check all expected dates exist
        for expected_date_str in expected_dates_str:
            if expected_date_str not in all_questions:
                raise ValueError(
                    f"Missing questions for date '{expected_date_str}'. "
                    f"Config expects questions for dates: {', '.join(expected_dates_str)}"
                )

        # Check each date has correct number of questions
        for date_str, questions in all_questions.items():
            if len(questions) != config.questions_per_day:
                raise ValueError(
                    f"Date '{date_str}' has {len(questions)} questions, "
                    f"expected {config.questions_per_day} (from config)"
                )
