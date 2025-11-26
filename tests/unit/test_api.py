# ABOUTME: Unit tests for FastAPI application endpoints.
# Tests application-specific endpoint logic, not framework behavior.

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
