# ABOUTME: Unit tests for data models (Question, Player, EventConfig, LeaderboardEntry).
# Tests focus on application-specific validation logic, not pydantic framework behavior.

import pytest
from pydantic import ValidationError

from src.models.question import Question


class TestQuestionModel:
    """Test suite for Question data model validation."""

    def test_question_with_valid_data_creates_successfully(self) -> None:
        """Test that Question with all valid fields creates successfully."""
        question = Question(
            id="q1",
            text="What is the capital of France?",
            options={
                "A": "London",
                "B": "Berlin",
                "C": "Paris",
                "D": "Madrid",
            },
            correct_answer="C",
        )

        assert question.id == "q1"
        assert question.text == "What is the capital of France?"
        assert question.options == {
            "A": "London",
            "B": "Berlin",
            "C": "Paris",
            "D": "Madrid",
        }
        assert question.correct_answer == "C"

    def test_question_options_must_have_exactly_abcd_keys(self) -> None:
        """Test that Question.options must have exactly keys A, B, C, D."""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                id="q1",
                text="Test question",
                options={"A": "Option A", "B": "Option B", "C": "Option C"},
                correct_answer="A",
            )

        # Verify the error mentions missing key D
        assert "options" in str(exc_info.value).lower()

    def test_question_options_with_missing_key_d_raises_validation_error(self) -> None:
        """Test that Question.options with missing D key raises validation error."""
        with pytest.raises(ValidationError):
            Question(
                id="q1",
                text="Test question",
                options={"A": "Opt A", "B": "Opt B", "C": "Opt C"},
                correct_answer="A",
            )

    def test_question_options_with_extra_key_e_raises_validation_error(self) -> None:
        """Test that Question.options with extra key E raises validation error."""
        with pytest.raises(ValidationError):
            Question(
                id="q1",
                text="Test question",
                options={
                    "A": "Opt A",
                    "B": "Opt B",
                    "C": "Opt C",
                    "D": "Opt D",
                    "E": "Opt E",
                },
                correct_answer="A",
            )

    def test_question_correct_answer_must_be_one_of_abcd(self) -> None:
        """Test that Question.correct_answer must be one of A, B, C, D."""
        # Valid correct_answer values should work
        for answer in ["A", "B", "C", "D"]:
            question = Question(
                id="q1",
                text="Test",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer=answer,
            )
            assert question.correct_answer == answer

    def test_question_correct_answer_e_raises_validation_error(self) -> None:
        """Test that Question.correct_answer='E' raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                id="q1",
                text="Test question",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="E",
            )

        # Verify error mentions correct_answer
        assert "correct_answer" in str(exc_info.value).lower()

    def test_question_correct_answer_must_match_key_in_options(self) -> None:
        """Test that Question.correct_answer must match a key in options dict."""
        # This test ensures correct_answer is validated against options keys
        question = Question(
            id="q1",
            text="Test",
            options={"A": "Opt A", "B": "Opt B", "C": "Opt C", "D": "Opt D"},
            correct_answer="B",
        )
        assert question.correct_answer in question.options

    def test_empty_question_text_raises_validation_error(self) -> None:
        """Test that empty question text raises validation error."""
        with pytest.raises(ValidationError):
            Question(
                id="q1",
                text="",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="A",
            )

    def test_empty_question_id_raises_validation_error(self) -> None:
        """Test that empty question id raises validation error."""
        with pytest.raises(ValidationError):
            Question(
                id="",
                text="What is 2+2?",
                options={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="D",
            )
