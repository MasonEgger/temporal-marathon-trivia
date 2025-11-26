# Marathon Trivia Platform - Development Commands
# Run 'just <command>' to execute

# Default recipe (show help)
default:
    @just --list

# Run all tests with coverage
test:
    uv run pytest

# Run unit tests only
test-unit:
    uv run pytest tests/unit/

# Run integration tests only (no coverage - tests run against real Temporal server)
test-integration:
    uv run pytest tests/integration/ --no-cov

# Run linter
lint:
    uv run ruff check src/ tests/

# Format code
format:
    uv run ruff format src/ tests/

# Run type checker
typecheck:
    uv run mypy --strict src/

# Run all checks (lint, typecheck, test)
check: lint typecheck test
