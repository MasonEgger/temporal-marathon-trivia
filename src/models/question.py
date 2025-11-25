# ABOUTME: Question data model for multiple choice trivia questions.
# Validates A/B/C/D answer format and correct answer selection.

from pydantic import field_validator, model_validator
from pydantic.dataclasses import dataclass


@dataclass
class Question:
    """
    Question data model for multiple choice trivia questions.

    Validates that questions follow the A/B/C/D answer format with exactly
    four options and a valid correct answer selection.

    Attributes:
        id: Unique identifier for the question
        text: The question text to display to players
        options: Dict mapping answer keys (A, B, C, D) to option text
        correct_answer: The correct answer key (must be A, B, C, or D)

    Raises:
        ValueError: If options dict doesn't have exactly keys A, B, C, D
        ValueError: If correct_answer is not one of A, B, C, D
        ValueError: If correct_answer doesn't match a key in options
        ValueError: If id or text are empty strings

    Examples:
        >>> question = Question(
        ...     id="q1",
        ...     text="What is 2+2?",
        ...     options={"A": "3", "B": "4", "C": "5", "D": "6"},
        ...     correct_answer="B"
        ... )
        >>> question.correct_answer
        'B'
    """

    id: str
    text: str
    options: dict[str, str]
    correct_answer: str

    @field_validator("id", "text")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate that id and text are non-empty strings."""
        if not v or not v.strip():
            raise ValueError("Field must be a non-empty string")
        return v

    @model_validator(mode="after")
    def validate_options(self) -> Question:
        """Validate that options has exactly keys A, B, C, D."""
        expected_keys = {"A", "B", "C", "D"}
        actual_keys = set(self.options.keys())

        if actual_keys != expected_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys

            error_parts = []
            if missing:
                error_parts.append(f"missing keys: {sorted(missing)}")
            if extra:
                error_parts.append(f"extra keys: {sorted(extra)}")

            raise ValueError(
                f"options must have exactly keys A, B, C, D. "
                f"Found issues: {', '.join(error_parts)}"
            )

        return self

    @model_validator(mode="after")
    def validate_correct_answer(self) -> Question:
        """Validate that correct_answer is one of A, B, C, D and exists in options."""
        valid_answers = {"A", "B", "C", "D"}

        if self.correct_answer not in valid_answers:
            raise ValueError(
                f"correct_answer must be one of A, B, C, D. "
                f"Got: {self.correct_answer!r}"
            )

        if self.correct_answer not in self.options:
            raise ValueError(
                f"correct_answer {self.correct_answer!r} must be a key in options dict. "
                f"Available keys: {sorted(self.options.keys())}"
            )

        return self
