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


class TestPlayerModel:
    """Test suite for Player data model validation."""

    def test_player_with_valid_data_creates_successfully(self) -> None:
        """Test that Player with valid data creates successfully."""
        from src.models.player import Player

        player = Player(
            id="player123",
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert player.id == "player123"
        assert player.email == "john.doe@example.com"
        assert player.first_name == "John"
        assert player.last_name == "Doe"
        assert player.total_score == 0
        assert player.daily_scores == {}
        assert player.completed_days == set()
        assert player.current_question_index == {}

    def test_player_get_display_name_returns_firstname_l_format(self) -> None:
        """Test that Player.get_display_name() returns 'FirstName L.' format."""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert player.get_display_name() == "John D."

    def test_player_get_display_name_with_john_doe_returns_john_d(self) -> None:
        """Test that get_display_name() with first_name='John', last_name='Doe' returns 'John D.'"""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="john.doe@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert player.get_display_name() == "John D."

    def test_player_get_display_name_with_empty_last_name_returns_first_name(
        self,
    ) -> None:
        """Test that get_display_name() with last_name='' returns just first_name."""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="john@example.com",
            first_name="John",
            last_name="",
        )

        assert player.get_display_name() == "John"

    def test_player_total_score_starts_at_zero_by_default(self) -> None:
        """Test that Player.total_score starts at 0 by default."""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        assert player.total_score == 0

    def test_player_daily_scores_is_empty_dict_by_default(self) -> None:
        """Test that Player.daily_scores is empty dict by default."""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        assert player.daily_scores == {}
        assert isinstance(player.daily_scores, dict)

    def test_player_completed_days_is_empty_set_by_default(self) -> None:
        """Test that Player.completed_days is empty set by default."""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        assert player.completed_days == set()
        assert isinstance(player.completed_days, set)

    def test_player_current_question_index_is_empty_dict_by_default(self) -> None:
        """Test that Player.current_question_index is empty dict by default."""
        from src.models.player import Player

        player = Player(
            id="p1",
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        assert player.current_question_index == {}
        assert isinstance(player.current_question_index, dict)

    def test_player_email_validation_requires_valid_email_format(self) -> None:
        """Test that Player.email validation requires valid email format."""
        from src.models.player import Player

        # Valid email should work
        player = Player(
            id="p1",
            email="valid@example.com",
            first_name="Test",
            last_name="User",
        )
        assert player.email == "valid@example.com"

    def test_invalid_email_raises_validation_error(self) -> None:
        """Test that invalid email raises validation error."""
        from src.models.player import Player

        with pytest.raises(ValidationError) as exc_info:
            Player(
                id="p1",
                email="not-an-email",
                first_name="Test",
                last_name="User",
            )

        # Verify error mentions email
        assert "email" in str(exc_info.value).lower()
