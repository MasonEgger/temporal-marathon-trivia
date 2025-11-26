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
