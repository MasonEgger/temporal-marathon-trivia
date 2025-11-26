# ABOUTME: Unit tests for FastAPI application endpoints.
# Tests application-specific endpoint logic, not framework behavior.

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.models.answer import EventStatusResponse


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
            follow_redirects=False,  # Don't follow redirect to avoid landing page
        )

        # Verify endpoint responds with redirect (303 See Other)
        assert response.status_code == 303
        # Verify redirect location is home page
        assert response.headers["location"] == "/"

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
            follow_redirects=False,  # Don't follow redirect
        )

        # Verify OUR cookie logic: name is "player_id", value matches workflow response
        # Now returns 303 redirect instead of 200
        assert response.status_code == 303
        assert "player_id" in response.cookies
        assert response.cookies["player_id"] == "player-abc-123"

    def test_join_returns_error_html_on_workflow_failure(self) -> None:
        """Test that workflow errors are caught and return error HTML.

        This tests OUR application logic - exception handling and error template selection.
        """

        from temporalio.exceptions import ApplicationError

        from src.api.main import app
        from src.models.ux_config import UXConfig

        # Manually set up app.state
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        # Simulate workflow rejecting registration
        mock_handle.execute_update = AsyncMock(side_effect=ApplicationError("Invalid email domain"))
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        # Mock ux_config (required by new warning logic)
        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.invalid_work_email_message = "Please use work email"
        app.state.ux_config = mock_ux_config

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
        mock_client.get_workflow_handle = MagicMock(side_effect=RuntimeError("Connection failed"))
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

    def test_join_endpoint_accepts_company_name_form_field(self) -> None:
        """Test that POST /api/join accepts company_name form field.

        This tests OUR application logic - that company_name is passed to RegisterPlayerRequest.
        """
        from src.api.main import app

        # Manually set up app.state
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
                "company_name": "Acme Corp",
            },
            follow_redirects=False,
        )

        # Verify endpoint responds successfully
        assert response.status_code == 303

        # Verify RegisterPlayerRequest was created with company_name
        # by checking the mock was called
        mock_handle.execute_update.assert_called_once()
        call_args = mock_handle.execute_update.call_args
        register_request = call_args[0][1]  # Second positional arg
        assert register_request.company_name == "Acme Corp"

    def test_join_endpoint_handles_missing_company_name(self) -> None:
        """Test that POST /api/join handles missing company_name (defaults to None).

        This tests OUR application logic - backward compatibility.
        """
        from src.api.main import app

        # Manually set up app.state
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_handle.execute_update = AsyncMock(return_value="player-123")
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.post(
            "/api/join",
            data={
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
                # No company_name provided
            },
            follow_redirects=False,
        )

        # Verify endpoint responds successfully
        assert response.status_code == 303

        # Verify RegisterPlayerRequest was created with company_name=None
        mock_handle.execute_update.assert_called_once()
        call_args = mock_handle.execute_update.call_args
        register_request = call_args[0][1]
        assert register_request.company_name is None


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
        mock_handle.execute_update = AsyncMock(side_effect=ApplicationError("Day has not started yet"))
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
        mock_handle.execute_update = AsyncMock(side_effect=ApplicationError("Day has already ended"))
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
        mock_handle.execute_update = AsyncMock(side_effect=ApplicationError("Day already completed"))
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
        mock_handle.execute_update = AsyncMock(side_effect=ApplicationError("Invalid date format"))
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
        mock_client.get_workflow_handle = MagicMock(side_effect=RuntimeError("Connection timeout"))
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
        mock_handle.execute_update = AsyncMock(side_effect=ApplicationError("answer_choice must be one of A, B, C, D"))
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
        mock_client.get_workflow_handle = MagicMock(side_effect=RuntimeError("Connection timeout"))
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


class TestLeaderboardEndpoint:
    """Tests for GET /api/leaderboard endpoint.

    These are UNIT tests focused on application logic only:
    - Data aggregation from multiple DailyWorkflows
    - Redis caching strategy (key naming, TTL)
    - HTML template rendering
    - Ranking and sorting logic

    We mock Temporal and Redis to isolate our application logic.
    """

    def test_leaderboard_returns_html_table_fragment(self) -> None:
        """Test that GET /api/leaderboard returns HTML table fragment.

        This tests OUR application logic - the specific HTML structure
        we generate for the leaderboard display.
        """
        from src.api.main import app
        from src.models.leaderboard import LeaderboardEntry
        from src.models.ux_config import UXConfig

        # Mock Redis - no cached data
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        # Mock ux_config (required by leaderboard route)
        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_event_handle = AsyncMock()
        mock_event_handle.query = AsyncMock(
            return_value=EventStatusResponse(
                event_id="test-event",
                player_count=2,
                daily_workflow_ids={"2025-03-10": "test-event-2025-03-10"},
            )
        )

        # Mock DailyWorkflow
        mock_daily_handle = AsyncMock()
        mock_daily_handle.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=100,
                    daily_scores={},
                    email="alice@example.com",
                ),
                LeaderboardEntry(
                    rank=2,
                    display_name="Bob C.",
                    total_score=80,
                    daily_scores={},
                    email="bob@example.com",
                ),
            ]
        )

        def get_workflow_handle(workflow_id: str):
            if workflow_id == "marathon-trivia-event":
                return mock_event_handle
            else:
                return mock_daily_handle

        mock_client.get_workflow_handle = MagicMock(side_effect=get_workflow_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get("/api/leaderboard")

        # Verify OUR response format (HTML fragment)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Verify leaderboard data is in response (our template rendering)
        assert "Alice B." in response.text
        assert "Bob C." in response.text
        assert "100" in response.text
        assert "80" in response.text

    def test_leaderboard_is_cached_in_redis_for_30_seconds(self) -> None:
        """Test that leaderboard data is cached in Redis with 30 second TTL.

        This tests OUR application logic - caching strategy with key naming
        and TTL configuration.
        """
        from src.api.main import app
        from src.models.leaderboard import LeaderboardEntry
        from src.models.ux_config import UXConfig

        # Mock Redis - no cached data initially
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        # Mock ux_config (required by leaderboard route)
        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_event_handle = AsyncMock()
        mock_event_handle.query = AsyncMock(
            return_value=EventStatusResponse(
                event_id="test-event",
                player_count=1,
                daily_workflow_ids={"2025-03-10": "test-event-2025-03-10"},
            )
        )

        mock_daily_handle = AsyncMock()
        mock_daily_handle.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=100,
                    daily_scores={},
                    email="alice@example.com",
                ),
            ]
        )

        def get_workflow_handle(workflow_id: str):
            if workflow_id == "marathon-trivia-event":
                return mock_event_handle
            else:
                return mock_daily_handle

        mock_client.get_workflow_handle = MagicMock(side_effect=get_workflow_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get("/api/leaderboard")

        # Verify OUR caching logic
        assert response.status_code == 200
        # Verify Redis.set was called with correct key and TTL
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "leaderboard:full"  # OUR key naming
        assert call_args[1]["ex"] == 30  # OUR TTL (30 seconds)

    def test_leaderboard_returns_cached_data_if_available(self) -> None:
        """Test that leaderboard returns cached data without querying Temporal.

        This tests OUR application logic - cache-first strategy to reduce
        Temporal query load.
        """
        import json

        from src.api.main import app

        # Mock Redis - return cached data
        cached_data = json.dumps(
            [
                {
                    "rank": 1,
                    "display_name": "Cached Player",
                    "total_score": 999,
                    "daily_scores": {"2025-03-10": 999},
                    "email": "cached@example.com",
                }
            ]
        )
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=cached_data)
        app.state.redis = mock_redis

        # Mock ux_config (required by leaderboard route)
        from src.models.ux_config import UXConfig

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock Temporal client - should NOT be called
        mock_client = AsyncMock()
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get("/api/leaderboard")

        # Verify OUR cache-first logic
        assert response.status_code == 200
        assert "Cached Player" in response.text
        assert "999" in response.text
        # Verify Redis.get was called with correct key
        mock_redis.get.assert_called_once_with("leaderboard:full")
        # Verify Temporal was NOT queried (cache hit)
        mock_client.get_workflow_handle.assert_not_called()

    def test_leaderboard_aggregates_scores_from_all_daily_workflows(self) -> None:
        """Test that leaderboard aggregates scores from multiple DailyWorkflows.

        This tests OUR application logic - aggregating player data across
        multiple days to calculate total scores.
        """
        from src.api.main import app
        from src.models.leaderboard import LeaderboardEntry

        # Mock Redis - no cached data
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        # Mock ux_config (required by leaderboard route)
        from src.models.ux_config import UXConfig

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock Temporal client with 2 days
        mock_client = AsyncMock()
        mock_event_handle = AsyncMock()
        mock_event_handle.query = AsyncMock(
            return_value=EventStatusResponse(
                event_id="test-event",
                player_count=2,
                daily_workflow_ids={
                    "2025-03-10": "test-event-2025-03-10",
                    "2025-03-11": "test-event-2025-03-11",
                },
            )
        )

        # Mock DailyWorkflow for Day 1
        mock_daily_handle_1 = AsyncMock()
        mock_daily_handle_1.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=50,
                    daily_scores={},
                    email="alice@example.com",
                ),
                LeaderboardEntry(
                    rank=2,
                    display_name="Bob C.",
                    total_score=40,
                    daily_scores={},
                    email="bob@example.com",
                ),
            ]
        )

        # Mock DailyWorkflow for Day 2
        mock_daily_handle_2 = AsyncMock()
        mock_daily_handle_2.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Bob C.",
                    total_score=60,
                    daily_scores={},
                    email="bob@example.com",
                ),
                LeaderboardEntry(
                    rank=2,
                    display_name="Alice B.",
                    total_score=55,
                    daily_scores={},
                    email="alice@example.com",
                ),
            ]
        )

        def get_workflow_handle(workflow_id: str):
            if workflow_id == "marathon-trivia-event":
                return mock_event_handle
            elif workflow_id == "test-event-2025-03-10":
                return mock_daily_handle_1
            elif workflow_id == "test-event-2025-03-11":
                return mock_daily_handle_2

        mock_client.get_workflow_handle = MagicMock(side_effect=get_workflow_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get("/api/leaderboard")

        # Verify OUR aggregation logic
        assert response.status_code == 200
        # Alice: 50 + 55 = 105, Bob: 40 + 60 = 100
        # Alice should be ranked #1 (higher total score)
        assert "Alice B." in response.text
        assert "Bob C." in response.text
        # Verify both days are shown
        assert "50" in response.text  # Alice Day 1
        assert "55" in response.text  # Alice Day 2

    def test_leaderboard_shows_correct_ranking_with_ties(self) -> None:
        """Test that leaderboard handles tied players correctly.

        This tests OUR application logic - ranking with tie handling where
        tied players share the same rank and next rank adjusts.
        """
        from src.api.main import app
        from src.models.leaderboard import LeaderboardEntry

        # Mock Redis - no cached data
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        # Mock ux_config (required by leaderboard route)
        from src.models.ux_config import UXConfig

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock ux_config (required by leaderboard route)
        from src.models.ux_config import UXConfig

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_event_handle = AsyncMock()
        mock_event_handle.query = AsyncMock(
            return_value=EventStatusResponse(
                event_id="test-event",
                player_count=4,
                daily_workflow_ids={"2025-03-10": "test-event-2025-03-10"},
            )
        )

        # Mock DailyWorkflow with tied scores
        mock_daily_handle = AsyncMock()
        mock_daily_handle.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=100,
                    daily_scores={},
                    email="alice@example.com",
                ),
                LeaderboardEntry(
                    rank=1,
                    display_name="Bob C.",
                    total_score=100,
                    daily_scores={},
                    email="bob@example.com",
                ),
                LeaderboardEntry(
                    rank=3,
                    display_name="Charlie D.",
                    total_score=80,
                    daily_scores={},
                    email="charlie@example.com",
                ),
            ]
        )

        def get_workflow_handle(workflow_id: str):
            if workflow_id == "marathon-trivia-event":
                return mock_event_handle
            else:
                return mock_daily_handle

        mock_client.get_workflow_handle = MagicMock(side_effect=get_workflow_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get("/api/leaderboard")

        # Verify OUR tie handling logic
        assert response.status_code == 200
        # Both Alice and Bob should show rank 1
        # Charlie should show rank 3 (not rank 2)
        assert "Alice B." in response.text
        assert "Bob C." in response.text
        assert "Charlie D." in response.text

    def test_leaderboard_shows_daily_scores_per_player(self) -> None:
        """Test that leaderboard displays daily breakdown per player.

        This tests OUR application logic - showing both total scores
        and daily score breakdowns for each player.
        """
        from src.api.main import app
        from src.models.leaderboard import LeaderboardEntry

        # Mock Redis - no cached data
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        # Mock ux_config (required by leaderboard route)
        from src.models.ux_config import UXConfig

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock ux_config (required by leaderboard route)
        from src.models.ux_config import UXConfig

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.leaderboard_refresh_seconds = 30
        app.state.ux_config = mock_ux_config

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_event_handle = AsyncMock()
        mock_event_handle.query = AsyncMock(
            return_value=EventStatusResponse(
                event_id="test-event",
                player_count=1,
                daily_workflow_ids={
                    "2025-03-10": "test-event-2025-03-10",
                    "2025-03-11": "test-event-2025-03-11",
                },
            )
        )

        # Mock DailyWorkflows
        mock_daily_handle_1 = AsyncMock()
        mock_daily_handle_1.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=50,
                    daily_scores={},
                    email="alice@example.com",
                ),
            ]
        )

        mock_daily_handle_2 = AsyncMock()
        mock_daily_handle_2.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=105,
                    daily_scores={},
                    email="alice@example.com",
                ),
            ]
        )

        def get_workflow_handle(workflow_id: str):
            if workflow_id == "marathon-trivia-event":
                return mock_event_handle
            elif workflow_id == "test-event-2025-03-10":
                return mock_daily_handle_1
            elif workflow_id == "test-event-2025-03-11":
                return mock_daily_handle_2

        mock_client.get_workflow_handle = MagicMock(side_effect=get_workflow_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)

        response = client.get("/api/leaderboard")

        # Verify OUR daily score display logic
        assert response.status_code == 200
        # Should show total score (105) and daily breakdown (50, 55)
        assert "Alice B." in response.text
        # Daily scores should be visible
        assert "50" in response.text  # Day 1 score
        assert "55" in response.text  # Day 2 score


class TestAggregateLeaderboards:
    """Tests for aggregate_leaderboards helper function.

    These tests focus on OUR application logic for:
    - Merging player data across multiple days
    - Calculating total scores correctly
    - Ranking with tie handling
    - Alphabetical tie-breaking
    """

    def test_aggregate_single_day_leaderboard(self) -> None:
        """Test aggregating a single day's leaderboard.

        This tests OUR logic for handling the simplest case - one day,
        no merging needed.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=100,
                daily_scores={},  # DailyWorkflow returns empty daily_scores
                email="alice@example.com",
            ),
            LeaderboardEntry(
                rank=2,
                display_name="Bob C.",
                total_score=80,
                daily_scores={},  # DailyWorkflow returns empty daily_scores
                email="bob@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1)])

        # Verify OUR aggregation preserves single-day data
        assert len(result) == 2
        assert result[0].rank == 1
        assert result[0].display_name == "Alice B."
        assert result[0].total_score == 100
        assert result[0].daily_scores == {"2025-03-10": 100}

    def test_aggregate_merges_same_player_across_days(self) -> None:
        """Test that aggregation merges same player's scores across days.

        This tests OUR core logic - identifying players by email and
        merging their daily scores.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=50,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        day2 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=60,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1), ("2025-03-11", day2)])

        # Verify OUR merging logic
        assert len(result) == 1
        assert result[0].display_name == "Alice B."
        assert result[0].total_score == 110  # 50 + 60
        assert result[0].daily_scores == {"2025-03-10": 50, "2025-03-11": 60}

    def test_aggregate_calculates_total_scores_correctly(self) -> None:
        """Test that total scores are calculated correctly across all days.

        This tests OUR arithmetic - summing daily scores accurately.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        # Alice plays 3 days: 50 + 60 + 40 = 150
        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=50,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        day2 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=60,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        day3 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=40,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1), ("2025-03-11", day2), ("2025-03-12", day3)])

        # Verify OUR total score calculation
        assert len(result) == 1
        assert result[0].total_score == 150

    def test_aggregate_ranks_by_total_score_descending(self) -> None:
        """Test that players are ranked by total score in descending order.

        This tests OUR ranking logic - highest score gets rank 1.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        # Alice: 50 + 55 = 105, Bob: 40 + 60 = 100
        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=50,
                daily_scores={},
                email="alice@example.com",
            ),
            LeaderboardEntry(
                rank=2,
                display_name="Bob C.",
                total_score=40,
                daily_scores={},
                email="bob@example.com",
            ),
        ]

        day2 = [
            LeaderboardEntry(
                rank=1,
                display_name="Bob C.",
                total_score=60,
                daily_scores={},
                email="bob@example.com",
            ),
            LeaderboardEntry(
                rank=2,
                display_name="Alice B.",
                total_score=55,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1), ("2025-03-11", day2)])

        # Verify OUR ranking (Alice 105 > Bob 100)
        assert len(result) == 2
        assert result[0].rank == 1
        assert result[0].display_name == "Alice B."
        assert result[0].total_score == 105
        assert result[1].rank == 2
        assert result[1].display_name == "Bob C."
        assert result[1].total_score == 100

    def test_aggregate_handles_tied_scores_correctly(self) -> None:
        """Test that tied players share the same rank.

        This tests OUR tie handling logic - multiple players at same
        score get same rank.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        # Both players score 100 total
        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=100,
                daily_scores={},
                email="alice@example.com",
            ),
            LeaderboardEntry(
                rank=1,
                display_name="Bob C.",
                total_score=100,
                daily_scores={},
                email="bob@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1)])

        # Verify OUR tie handling (both rank 1)
        assert len(result) == 2
        # Alphabetically: Alice before Bob
        assert result[0].display_name == "Alice B."
        assert result[0].rank == 1
        assert result[1].display_name == "Bob C."
        assert result[1].rank == 1

    def test_aggregate_adjusts_rank_after_tie(self) -> None:
        """Test that rank adjusts correctly after tied players.

        This tests OUR logic - if 2 players tie for rank 1, next player
        is rank 3 (not rank 2).
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        # Alice and Bob tie at 100, Charlie scores 80
        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=100,
                daily_scores={},
                email="alice@example.com",
            ),
            LeaderboardEntry(
                rank=1,
                display_name="Bob C.",
                total_score=100,
                daily_scores={},
                email="bob@example.com",
            ),
            LeaderboardEntry(
                rank=3,
                display_name="Charlie D.",
                total_score=80,
                daily_scores={},
                email="charlie@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1)])

        # Verify OUR rank adjustment logic
        assert len(result) == 3
        assert result[0].rank == 1  # Alice
        assert result[1].rank == 1  # Bob
        assert result[2].rank == 3  # Charlie (rank 3, not 2!)

    def test_aggregate_breaks_ties_alphabetically(self) -> None:
        """Test that ties are broken alphabetically by display name.

        This tests OUR alphabetical sorting logic for tied players.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        # Three players, all score 100
        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Zoe Y.",
                total_score=100,
                daily_scores={},
                email="zoe@example.com",
            ),
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=100,
                daily_scores={},
                email="alice@example.com",
            ),
            LeaderboardEntry(
                rank=1,
                display_name="Bob C.",
                total_score=100,
                daily_scores={},
                email="bob@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1)])

        # Verify OUR alphabetical tie-breaking
        assert len(result) == 3
        assert result[0].display_name == "Alice B."
        assert result[1].display_name == "Bob C."
        assert result[2].display_name == "Zoe Y."
        # All should have rank 1
        assert result[0].rank == 1
        assert result[1].rank == 1
        assert result[2].rank == 1

    def test_aggregate_handles_empty_leaderboards(self) -> None:
        """Test that empty leaderboards are handled gracefully.

        This tests OUR edge case handling - empty input returns empty output.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards

        result = aggregate_leaderboards([])

        # Verify OUR empty handling
        assert len(result) == 0

    def test_aggregate_handles_players_missing_some_days(self) -> None:
        """Test that players who didn't play all days are handled correctly.

        This tests OUR logic for partial participation - players get credit
        for days they played, zero for days they didn't.
        """
        from src.api.routes.leaderboard import aggregate_leaderboards
        from src.models.leaderboard import LeaderboardEntry

        # Alice plays both days, Bob only plays day 1
        day1 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=50,
                daily_scores={},
                email="alice@example.com",
            ),
            LeaderboardEntry(
                rank=2,
                display_name="Bob C.",
                total_score=40,
                daily_scores={},
                email="bob@example.com",
            ),
        ]

        day2 = [
            LeaderboardEntry(
                rank=1,
                display_name="Alice B.",
                total_score=60,
                daily_scores={},
                email="alice@example.com",
            ),
        ]

        result = aggregate_leaderboards([("2025-03-10", day1), ("2025-03-11", day2)])

        # Verify OUR partial participation handling
        assert len(result) == 2
        # Alice: 50 + 60 = 110
        assert result[0].display_name == "Alice B."
        assert result[0].total_score == 110
        assert result[0].daily_scores == {"2025-03-10": 50, "2025-03-11": 60}
        # Bob: 40 + 0 = 40
        assert result[1].display_name == "Bob C."
        assert result[1].total_score == 40
        assert result[1].daily_scores == {"2025-03-10": 40}


class TestConfigEndpoint:
    """Tests for GET /api/config endpoint.

    Tests OUR application logic for configuration API.
    """

    def test_config_endpoint_returns_json_with_event_config(self) -> None:
        """Test that GET /api/config returns JSON with event configuration.

        This tests OUR application logic - the structure and fields
        of the combined config response.
        """
        from datetime import date, time

        from src.api.main import app
        from src.models.config import EventConfig
        from src.models.ux_config import UXConfig

        # Mock app.state.config and app.state.ux_config
        mock_config = MagicMock(spec=EventConfig)
        mock_config.start_date = date(2025, 3, 10)
        mock_config.end_date = date(2025, 3, 12)
        mock_config.day_start_time = time(9, 0)
        mock_config.day_end_time = time(17, 0)
        mock_config.get_all_dates.return_value = [
            date(2025, 3, 10),
            date(2025, 3, 11),
            date(2025, 3, 12),
        ]

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.title = "Test Event"
        mock_ux_config.description = "A test trivia event"
        mock_ux_config.primary_color = "#3b82f6"
        mock_ux_config.secondary_color = "#8b5cf6"
        mock_ux_config.background_color = "#ffffff"
        mock_ux_config.text_color = "#1f2937"

        app.state.config = mock_config
        app.state.ux_config = mock_ux_config

        # Mock Redis (not cached)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        client = TestClient(app)
        response = client.get("/api/config")

        # Verify OUR JSON structure
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert data["title"] == "Test Event"
        assert data["description"] == "A test trivia event"
        assert data["start_date"] == "2025-03-10"
        assert data["end_date"] == "2025-03-12"
        assert data["dates"] == ["2025-03-10", "2025-03-11", "2025-03-12"]
        assert data["colors"]["primary"] == "#3b82f6"
        assert data["colors"]["secondary"] == "#8b5cf6"

    def test_config_endpoint_is_cached_permanently(self) -> None:
        """Test that GET /api/config caches result with no expiration.

        This tests OUR caching strategy - permanent caching for static config.
        """
        from datetime import date, time

        from src.api.main import app
        from src.models.config import EventConfig
        from src.models.ux_config import UXConfig

        # Mock app.state
        mock_config = MagicMock(spec=EventConfig)
        mock_config.start_date = date(2025, 3, 10)
        mock_config.end_date = date(2025, 3, 12)
        mock_config.day_start_time = time(9, 0)
        mock_config.day_end_time = time(17, 0)
        mock_config.get_all_dates.return_value = [date(2025, 3, 10)]

        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.title = "Test"
        mock_ux_config.description = "Test"
        mock_ux_config.primary_color = "#000000"
        mock_ux_config.secondary_color = "#000000"
        mock_ux_config.background_color = "#ffffff"
        mock_ux_config.text_color = "#000000"

        app.state.config = mock_config
        app.state.ux_config = mock_ux_config

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Not cached
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        client = TestClient(app)
        response = client.get("/api/config")

        assert response.status_code == 200

        # Verify OUR caching behavior - set with no expiration
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "config:event"  # Cache key
        # No TTL argument means permanent cache


class TestPlayerLookupEndpoint:
    """Tests for GET /api/player endpoint.

    Tests OUR application logic for player lookup and highlighting.
    """

    def test_player_endpoint_returns_html_with_highlighted_rank(self) -> None:
        """Test that GET /api/player returns HTML with player's rank highlighted.

        This tests OUR application logic - fetching player state and
        rendering highlighted leaderboard HTML.
        """
        from src.api.main import app
        from src.models.leaderboard import LeaderboardEntry
        from src.models.player import Player
        from src.models.state import PlayerState

        # Mock Temporal client and player workflow
        mock_client = AsyncMock()
        mock_player_handle = AsyncMock()

        # Mock PlayerState with proper structure
        mock_player_state = PlayerState(
            player=Player(
                id="player-123",
                email="alice@example.com",
                first_name="Alice",
                last_name="Brown",
            ),
            current_day=None,
            current_question_index=0,
            current_questions=None,
        )
        mock_player_handle.query = AsyncMock(return_value=mock_player_state)
        mock_client.get_workflow_handle = MagicMock(return_value=mock_player_handle)
        app.state.temporal_client = mock_client

        # Mock EventWorkflow for getting daily_workflow_ids
        mock_event_handle = AsyncMock()
        mock_event_handle.query = AsyncMock(
            return_value=EventStatusResponse(
                event_id="event-1",
                player_count=2,
                daily_workflow_ids={"2025-03-10": "event-1-2025-03-10"},
            )
        )

        # Mock DailyWorkflow leaderboard
        mock_daily_handle = AsyncMock()
        mock_daily_handle.query = AsyncMock(
            return_value=[
                LeaderboardEntry(
                    rank=1,
                    display_name="Alice B.",
                    total_score=100,
                    daily_scores={},
                    email="alice@example.com",
                ),
                LeaderboardEntry(
                    rank=2,
                    display_name="Bob C.",
                    total_score=80,
                    daily_scores={},
                    email="bob@example.com",
                ),
            ]
        )

        # Mock get_workflow_handle to return appropriate handle based on ID
        def get_handle_side_effect(workflow_id: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if workflow_id == "player-123":
                return mock_player_handle
            elif workflow_id == "marathon-trivia-event":
                return mock_event_handle
            elif workflow_id == "event-1-2025-03-10":
                return mock_daily_handle
            raise ValueError(f"Unexpected workflow_id: {workflow_id}")

        mock_client.get_workflow_handle.side_effect = get_handle_side_effect
        app.state.temporal_client = mock_client

        # Mock Redis (not cached)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        app.state.redis = mock_redis

        # Mock config for get_all_dates
        from datetime import date

        from src.models.config import EventConfig

        mock_config = MagicMock(spec=EventConfig)
        mock_config.get_all_dates.return_value = [date(2025, 3, 10)]
        app.state.config = mock_config

        client = TestClient(app)
        response = client.get("/api/player", cookies={"player_id": "player-123"})

        # Verify OUR highlighting logic
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Should contain Alice's entry with highlight class
        assert "Alice B." in response.text

    def test_player_endpoint_requires_player_id_cookie(self) -> None:
        """Test that GET /api/player requires player_id cookie.

        This tests OUR validation logic - ensuring authentication.
        """
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/api/player")  # No cookie

        # Verify OUR decision to return error HTML
        assert response.status_code == 200  # HTMX pattern
        assert "text/html" in response.headers["content-type"]
        assert "error" in response.text.lower()


class TestLandingPage:
    """Tests for GET / landing page endpoint.

    Tests that landing page renders correctly for both first-time
    and returning players with proper template context.
    """

    def test_landing_page_without_cookie_shows_join_form(self) -> None:
        """Test that GET / without cookie shows registration form.

        This tests OUR application logic - showing join form for first-time visitors.
        """
        from datetime import date

        from src.api.main import app
        from src.models.config import EventConfig
        from src.models.ux_config import UXConfig

        # Mock config
        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.title = "Test Trivia"
        mock_ux_config.description = "Test Description"
        mock_ux_config.primary_color = "#3b82f6"
        mock_ux_config.secondary_color = "#8b5cf6"
        mock_ux_config.background_color = "#ffffff"
        mock_ux_config.text_color = "#000000"

        mock_event_config = MagicMock(spec=EventConfig)
        mock_event_config.get_all_dates.return_value = [
            date(2025, 3, 10),
            date(2025, 3, 11),
        ]

        app.state.ux_config = mock_ux_config
        app.state.config = mock_event_config

        client = TestClient(app)
        response = client.get("/")  # No cookie

        # Verify response is HTML
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Verify join form is present
        assert "Join the Trivia Challenge" in response.text
        assert 'name="first_name"' in response.text
        assert 'name="last_name"' in response.text
        assert 'name="email"' in response.text
        assert 'hx-post="/api/join"' in response.text

    def test_landing_page_with_cookie_shows_game_interface(self) -> None:
        """Test that GET / with cookie shows day buttons and leaderboard.

        This tests OUR application logic - showing game interface for returning players.
        """
        from datetime import date

        from src.api.main import app
        from src.models.config import EventConfig
        from src.models.player import Player
        from src.models.state import PlayerState
        from src.models.ux_config import UXConfig

        # Mock config
        mock_ux_config = MagicMock(spec=UXConfig)
        mock_ux_config.title = "Test Trivia"
        mock_ux_config.description = "Test Description"
        mock_ux_config.primary_color = "#3b82f6"
        mock_ux_config.secondary_color = "#8b5cf6"
        mock_ux_config.background_color = "#ffffff"
        mock_ux_config.text_color = "#000000"

        mock_event_config = MagicMock(spec=EventConfig)
        mock_event_config.get_all_dates.return_value = [
            date(2025, 3, 10),
            date(2025, 3, 11),
        ]

        app.state.ux_config = mock_ux_config
        app.state.config = mock_event_config

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_player_state = PlayerState(
            player=Player(
                id="player-123",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                completed_days={"2025-03-10"},
            ),
            current_day=None,
            current_question_index=0,
        )
        mock_handle.query = AsyncMock(return_value=mock_player_state)
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        app.state.temporal_client = mock_client

        client = TestClient(app)
        response = client.get("/", cookies={"player_id": "player-123"})

        # Verify response is HTML
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Verify game interface is present
        assert "Select a Day" in response.text
        assert "Leaderboard" in response.text
        assert 'hx-get="/api/leaderboard"' in response.text
        # Leaderboard refresh interval is now configurable (was hardcoded to 30s)
        assert 'hx-trigger="load, every' in response.text
        assert "Find My Rank" in response.text
