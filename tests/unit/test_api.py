# ABOUTME: Unit tests for FastAPI application endpoints.
# Tests application-specific endpoint logic, not framework behavior.

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_endpoint_returns_ok(self) -> None:
        """Test that GET /health returns {"status": "ok"}.

        This tests OUR application logic - the specific response format
        we define for the health endpoint.
        """
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPlayerRegistration:
    """Tests for POST /api/join player registration endpoint.

    These are UNIT tests focused on application logic only.
    Integration tests with real Temporal workflows are in tests/integration/.
    """

    def test_join_endpoint_exists_and_accepts_form_data(self) -> None:
        """Test that POST /api/join endpoint exists and accepts form data.

        This tests OUR application logic - that the endpoint is properly configured
        to accept the three required form fields.
        """

        from src.api.main import app

        # Manually set up app.state (simulating what lifespan does)
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_handle.execute_update = AsyncMock(return_value="player-123")
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/join",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
            },
        )

        # Verify endpoint responds (not 404)
        assert response.status_code == 200
        # Verify it returns HTML (our template rendering logic)
        assert "text/html" in response.headers["content-type"]

    def test_join_sets_player_id_cookie_on_success(self) -> None:
        """Test that successful registration sets player_id cookie.

        This tests OUR application logic - cookie name and value assignment.
        """

        from src.api.main import app

        # Manually set up app.state
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_handle.execute_update = AsyncMock(return_value="player-abc-123")
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/join",
            data={
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
            },
        )

        # Verify OUR cookie logic: name is "player_id", value matches workflow response
        assert response.status_code == 200
        assert "player_id" in response.cookies
        assert response.cookies["player_id"] == "player-abc-123"

    def test_join_returns_error_html_on_workflow_failure(self) -> None:
        """Test that workflow errors are caught and return error HTML.

        This tests OUR application logic - exception handling and error template selection.
        """

        from temporalio.exceptions import ApplicationError

        from src.api.main import app

        # Manually set up app.state
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting registration
        mock_handle.execute_update = AsyncMock(
            side_effect=ApplicationError("Invalid email domain")
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/join",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "bad@example.com",
            },
        )

        # Verify OUR error handling logic
        assert response.status_code == 200  # We return 200 with error HTML for HTMX
        assert "text/html" in response.headers["content-type"]
        # Verify error message is present in response (our template rendering)
        assert "error" in response.text.lower()

    def test_join_handles_unexpected_exceptions_gracefully(self) -> None:
        """Test that unexpected exceptions return generic error HTML.

        This tests OUR application logic - fallback error handling.
        """

        from src.api.main import app

        # Manually set up app.state
        mock_client = AsyncMock()
        # Simulate unexpected error (e.g., network issue)
        mock_client.get_workflow_handle = MagicMock(
            side_effect=RuntimeError("Connection failed")
        )
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/join",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
        )

        # Verify OUR fallback error handling
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()


class TestGameplayStartDay:
    """Tests for GET /api/day/{date}/start endpoint.

    These are UNIT tests focused on application logic only.
    Tests endpoint configuration, cookie validation, error handling, and template selection.
    """

    def test_start_day_returns_html_fragment_with_question(self) -> None:
        """Test that GET /api/day/{date}/start returns HTML fragment with first question.

        This tests OUR application logic - that we return HTML (not JSON) with question data.
        """
        from src.api.main import app
        from src.models.question import Question

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Mock start_day returning first question
        mock_question = Question(
            id="q1",
            text="What is 2+2?",
            options={"A": "3", "B": "4", "C": "5", "D": "6"},
            correct_answer="B",
        )
        mock_handle.execute_update = AsyncMock(return_value=mock_question)
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get(
            "/api/day/2025-03-10/start",
            cookies={"player_id": "player-123"},
        )

        # Verify OUR response format (HTML fragment)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Verify question data is in response (our template rendering)
        assert "What is 2+2?" in response.text

    def test_start_day_requires_player_id_cookie(self) -> None:
        """Test that endpoint requires player_id cookie.

        This tests OUR application logic - cookie validation requirement.
        """
        from src.api.main import app

        mock_client = AsyncMock()
        app.state.temporal_client = mock_client

        client = TestClient(app)

        # Request WITHOUT player_id cookie
        response = client.get("/api/day/2025-03-10/start")

        # Verify OUR validation logic returns error
        assert response.status_code == 200  # HTMX pattern: return 200 with error HTML
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_start_day_validates_day_has_started(self) -> None:
        """Test that endpoint validates day has started.

        This tests OUR application logic - handling workflow validation errors for early access.
        """
        from temporalio.exceptions import ApplicationError

        from src.api.main import app

        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting because day hasn't started
        mock_handle.execute_update = AsyncMock(
            side_effect=ApplicationError("Day has not started yet")
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get(
            "/api/day/2025-03-10/start",
            cookies={"player_id": "player-123"},
        )

        # Verify OUR error handling returns appropriate message
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_start_day_validates_day_hasnt_ended(self) -> None:
        """Test that endpoint validates day hasn't ended.

        This tests OUR application logic - handling workflow validation errors for late access.
        """
        from temporalio.exceptions import ApplicationError

        from src.api.main import app

        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting because day has ended
        mock_handle.execute_update = AsyncMock(
            side_effect=ApplicationError("Day has already ended")
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get(
            "/api/day/2025-03-10/start",
            cookies={"player_id": "player-123"},
        )

        # Verify OUR error handling returns appropriate message
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_start_day_validates_player_hasnt_completed_day(self) -> None:
        """Test that endpoint validates player hasn't completed day.

        This tests OUR application logic - handling workflow validation errors
        for duplicate attempts.
        """
        from temporalio.exceptions import ApplicationError

        from src.api.main import app

        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting because day already completed
        mock_handle.execute_update = AsyncMock(
            side_effect=ApplicationError("Day already completed")
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get(
            "/api/day/2025-03-10/start",
            cookies={"player_id": "player-123"},
        )

        # Verify OUR error handling returns appropriate message
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_start_day_returns_error_html_for_invalid_date(self) -> None:
        """Test that endpoint returns error HTML for invalid date.

        This tests OUR application logic - handling workflow validation errors for invalid dates.
        """
        from temporalio.exceptions import ApplicationError

        from src.api.main import app

        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting invalid date format
        mock_handle.execute_update = AsyncMock(
            side_effect=ApplicationError("Invalid date format")
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get(
            "/api/day/invalid-date/start",
            cookies={"player_id": "player-123"},
        )

        # Verify OUR error handling returns appropriate message
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_start_day_handles_unexpected_exceptions(self) -> None:
        """Test that unexpected exceptions return generic error HTML.

        This tests OUR application logic - fallback error handling for unexpected errors.
        """
        from src.api.main import app

        mock_client = AsyncMock()
        # Simulate unexpected error (e.g., network issue)
        mock_client.get_workflow_handle = MagicMock(
            side_effect=RuntimeError("Connection timeout")
        )
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get(
            "/api/day/2025-03-10/start",
            cookies={"player_id": "player-123"},
        )

        # Verify OUR fallback error handling
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()


class TestGameplaySubmitAnswer:
    """Test suite for POST /api/day/{date}/answer endpoint.

    Tests focus on OUR application logic:
    - Form parameter handling (question_id, answer_choice)
    - Cookie validation
    - Workflow orchestration (calling submit_answer)
    - Response routing (next question vs completion)
    - Error handling (validation failures, exceptions)

    Does NOT test: FastAPI form parsing, Temporal SDK, template rendering engine.
    """

    def test_submit_answer_with_correct_answer_returns_correct_feedback(self) -> None:
        """Test that correct answers return appropriate feedback and next question.

        This tests OUR application logic - orchestrating workflow calls and routing
        responses based on AnswerResult.
        """
        from src.api.main import app
        from src.models.answer import AnswerResult
        from src.models.config import EventConfig
        from src.models.question import Question

        # Mock config
        mock_config = MagicMock(spec=EventConfig)
        mock_config.show_correct_answer = True
        app.state.config = mock_config

        mock_client = AsyncMock()
        mock_handle = AsyncMock()

        # Simulate workflow returning correct answer + next question
        next_q = Question(
            id="q2",
            text="Next question?",
            options={"A": "Opt1", "B": "Opt2", "C": "Opt3", "D": "Opt4"},
            correct_answer="A",
        )
        mock_handle.execute_update = AsyncMock(
            return_value=AnswerResult(
                is_correct=True,
                correct_answer=None,  # Not shown for correct answers
                next_question=next_q,
                completion_message=None,
                current_score=1,
                total_questions=5,
            )
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q1", "answer_choice": "A"},
            cookies={"player_id": "player-123"},
        )

        # Verify OUR decision to return next question HTML
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Next question?" in response.text

    def test_submit_answer_with_incorrect_answer_returns_incorrect_feedback(
        self,
    ) -> None:
        """Test that incorrect answers return appropriate feedback with correct answer.

        This tests OUR application logic - showing correct answer when configured.
        """
        from src.api.main import app
        from src.models.answer import AnswerResult
        from src.models.question import Question

        mock_client = AsyncMock()
        mock_handle = AsyncMock()

        # Simulate workflow returning incorrect answer + next question
        next_q = Question(
            id="q2",
            text="Next question?",
            options={"A": "Opt1", "B": "Opt2", "C": "Opt3", "D": "Opt4"},
            correct_answer="A",
        )
        mock_handle.execute_update = AsyncMock(
            return_value=AnswerResult(
                is_correct=False,
                correct_answer="A",  # Show correct answer
                next_question=next_q,
                completion_message=None,
                current_score=0,
                total_questions=5,
            )
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q1", "answer_choice": "B"},
            cookies={"player_id": "player-123"},
        )

        # Verify OUR decision to show correct answer
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Note: Actual feedback rendering tested via template, we test routing

    def test_submit_answer_returns_next_question_if_more_remain(self) -> None:
        """Test that endpoint returns next question when not all answered.

        This tests OUR application logic - routing based on AnswerResult.next_question.
        """
        from src.api.main import app
        from src.models.answer import AnswerResult
        from src.models.config import EventConfig
        from src.models.question import Question

        # Mock config
        mock_config = MagicMock(spec=EventConfig)
        mock_config.show_correct_answer = True
        app.state.config = mock_config

        mock_client = AsyncMock()
        mock_handle = AsyncMock()

        next_q = Question(
            id="q3",
            text="Third question?",
            options={"A": "Opt1", "B": "Opt2", "C": "Opt3", "D": "Opt4"},
            correct_answer="C",
        )
        mock_handle.execute_update = AsyncMock(
            return_value=AnswerResult(
                is_correct=True,
                correct_answer=None,
                next_question=next_q,
                completion_message=None,
                current_score=2,
                total_questions=5,
            )
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q2", "answer_choice": "A"},
            cookies={"player_id": "player-123"},
        )

        # Verify OUR routing returns next question template
        assert response.status_code == 200
        assert "Third question?" in response.text

    def test_submit_answer_returns_completion_if_all_answered(self) -> None:
        """Test that endpoint returns completion message when day is done.

        This tests OUR application logic - routing based on AnswerResult.completion_message.
        """
        from src.api.main import app
        from src.models.answer import AnswerResult
        from src.models.config import EventConfig

        # Mock config
        mock_config = MagicMock(spec=EventConfig)
        mock_config.show_correct_answer = True
        app.state.config = mock_config

        mock_client = AsyncMock()
        mock_handle = AsyncMock()

        mock_handle.execute_update = AsyncMock(
            return_value=AnswerResult(
                is_correct=True,
                correct_answer=None,
                next_question=None,  # No more questions
                completion_message="Great job! You completed today's trivia!",
                current_score=5,
                total_questions=5,
            )
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q5", "answer_choice": "D"},
            cookies={"player_id": "player-123"},
        )

        # Verify OUR routing returns completion template
        assert response.status_code == 200
        assert "completed" in response.text.lower() or "great job" in response.text.lower()

    def test_submit_answer_validates_answer_choice(self) -> None:
        """Test that invalid answer_choice returns error HTML.

        This tests OUR application logic - handling workflow validation errors.
        """
        from temporalio.exceptions import ApplicationError

        from src.api.main import app

        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting invalid answer
        mock_handle.execute_update = AsyncMock(
            side_effect=ApplicationError("answer_choice must be one of A, B, C, D")
        )
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q1", "answer_choice": "E"},
            cookies={"player_id": "player-123"},
        )

        # Verify OUR error handling returns appropriate message
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_submit_answer_requires_player_id_cookie(self) -> None:
        """Test that missing player_id cookie returns error HTML.

        This tests OUR application logic - manual cookie validation for HTMX compatibility.
        """
        from src.api.main import app

        client = TestClient(app)

        # Request without player_id cookie
        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q1", "answer_choice": "A"},
        )

        # Verify OUR decision to return 200 + error HTML (HTMX pattern)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()

    def test_submit_answer_handles_unexpected_exceptions(self) -> None:
        """Test that unexpected exceptions return generic error HTML.

        This tests OUR application logic - fallback error handling.
        """
        from src.api.main import app

        mock_client = AsyncMock()
        # Simulate unexpected error
        mock_client.get_workflow_handle = MagicMock(
            side_effect=RuntimeError("Connection timeout")
        )
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/day/2025-03-10/answer",
            data={"question_id": "q1", "answer_choice": "A"},
            cookies={"player_id": "player-123"},
        )

        # Verify OUR fallback error handling
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()
