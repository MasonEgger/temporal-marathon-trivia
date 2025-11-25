# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Marathon Trivia Platform is a web-based, multi-day trivia application designed for trade show booth engagement. It supports hundreds to thousands of concurrent players using Temporal workflows for state management.

**Use Case**: Trade show booth staff deploy this for 3-5 day conferences. Attendees join via QR code, answer daily questions at their own pace, and compete on a live leaderboard for prizes.

## Architecture

### Temporal Workflow Pattern (Entity Workflows)

The application uses a hierarchical workflow structure:

```
EventWorkflow (parent, entire event)
├── DailyWorkflow (child, per day)
│   ├── Receives score updates from players
│   └── Maintains daily leaderboard state
└── DailyWorkflow (child, per day)

PlayerEntityWorkflow (entity, per player)
├── Long-running workflow for entire event
├── Tracks current question, score, progress
└── Submits answers to DailyWorkflow via update handlers
```

**Key Pattern**: Event workflow spawns daily child workflows at configured times. Each player gets a persistent entity workflow that reports scores to the appropriate daily workflow. This enables:
- Player state persistence without external database
- Aggregated leaderboards at daily workflow level (don't query 1000s of players)
- Independent player progression (asynchronous gameplay)

### Component Stack

- **Backend**: Temporal Python SDK + FastAPI + Redis
- **Frontend**: HTMX + Tailwind CSS (minimal JavaScript)
- **Deployment**: Docker Compose with Temporal single binary
- **Config**: TOML for event settings, JSON for questions, .env for secrets
- **Storage**: S3 for CSV exports

### Directory Structure

- `src/workflows/`: EventWorkflow, DailyWorkflow, PlayerEntityWorkflow
- `src/activities/`: Config loading, question loading, email validation, S3 export
- `src/models/`: Question, Player, EventConfig, LeaderboardEntry dataclasses
- `src/api/`: FastAPI app with routes/, cache.py, templates.py
- `frontend/`: HTML templates and static assets (HTMX, Tailwind)
- `config/`: event.toml and questions.json (event-specific configuration)
- `tests/`: unit/, integration/, fixtures/

## Development Commands

All commands reference patterns from `temporal-trivia-python` (see Justfile when implemented):

### Running Services
```bash
just dev           # Start all services (Temporal, Redis, worker, API)
just worker        # Run Temporal worker only
just api           # Run FastAPI dev server with reload

# Non-containerized local dev
temporal server start-dev  # Start Temporal dev server
redis-server               # Start Redis
uv run python src/worker.py
uv run uvicorn src.api.main:app --reload
```

### Testing
```bash
just test              # Run all tests with pytest
just test-unit         # Run unit tests only
just test-integration  # Run integration tests only
just coverage          # Run tests with coverage report (minimum 80%)

# Run single test
uv run pytest tests/unit/test_workflows.py::test_player_workflow_tracks_score -v
```

### Linting & Type Checking
```bash
just lint       # Run ruff linter
just format     # Run ruff formatter
just typecheck  # Run mypy --strict type checker
```

### Docker
```bash
just build  # Build Docker image
just up     # Start Docker Compose stack
just down   # Stop Docker Compose stack
```

### Data Operations
```bash
just export-csv        # Manually trigger CSV export for today
just validate-config   # Validate TOML and questions JSON schemas
```

## Critical Implementation Details

### Question Data Format

Questions use **explicit letter keys** (not array indices) for robustness:

```json
{
  "2025-03-10": [
    {
      "id": "q1",
      "text": "What does EC2 stand for?",
      "options": {
        "A": "Elastic Compute Cloud",
        "B": "Elastic Container Cloud",
        "C": "Elastic Compute Cluster",
        "D": "Elastic Cloud Computing"
      },
      "correct_answer": "A"
    }
  ]
}
```

**Rationale**: Explicit A/B/C/D keys are safer for manual editing (no accidental reordering), easier to validate, and visually verifiable.

### Leaderboard Ranking

- Ranked by **total score** (sum across all days)
- **Tied players share the same rank** (e.g., 5 players tied for 1st = all rank 1)
- Next rank adjusts (if 5 at rank 1, next player is rank 6)
- Ties broken **alphabetically** by last name, then first name
- Display format: "FirstName L." (first name + last initial)

### Caching Strategy (Redis)

- **Leaderboard**: 30s TTL (matches frontend polling frequency)
- **Player state**: 10s TTL
- **Config**: No expiration (loaded at startup)

Cache keys:
- `leaderboard:full`
- `player:{player_id}:state`
- `config:event`

### API Endpoints Return HTML

All FastAPI endpoints return **HTML fragments** for HTMX (not JSON). This discourages external API usage and keeps the frontend simple.

Example:
```python
@router.post("/api/day/{date}/answer")
async def submit_answer(...) -> HTMLResponse:
    # Returns HTML fragment with next question or completion message
    return templates.TemplateResponse("question.html", ...)
```

## Testing Requirements

### Coverage & Approach

- **Minimum 80% code coverage** across all modules
- **TDD approach**: Write failing tests first, implement to pass, refactor
- Focus on **application logic only** (not framework behavior)

### Critical Testing Patterns (from temporal-trivia-python)

1. **Update handlers**: Test that updates return correct responses immediately
2. **Continue-as-new**: Use positional args for explicit state passing
3. **Time-skipping tests**: Use `asyncio.sleep()` after signals to allow processing
4. **Class-based activities with Protocol DI**: Enables clean mocking and testing
5. **Defensive queries**: Return `.copy()` to prevent external mutation
6. **Temporal test environment**: Reuse fixtures and setup patterns

### Test Organization

- **Unit tests**: Individual workflows, activities, models, API endpoints
- **Integration tests**: Full player journeys, multi-day flows, leaderboard aggregation
- **End-to-end tests**: Complete event lifecycle with time-based transitions

Example test names:
- `test_player_workflow_tracks_score()`
- `test_player_workflow_rejects_duplicate_answers()`
- `test_leaderboard_ranking_with_ties()`
- `test_full_player_journey()` (integration)

## Configuration

### Environment Variables (.env)

```bash
# Temporal connection
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=marathon-trivia

# Temporal Cloud (if applicable)
TEMPORAL_TLS_CERT_PATH=/path/to/cert.pem
TEMPORAL_TLS_KEY_PATH=/path/to/key.pem

# AWS credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Redis
REDIS_URL=redis://localhost:6379

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
```

### Event Configuration (config/event.toml)

```toml
[event]
title = "AWS re:Invent 2025 Trivia"
description = "Test your cloud knowledge and win prizes!"
base_url = "trivia.ziggy.codes"

[dates]
start_date = "2025-03-10"
end_date = "2025-03-14"
day_start_time = "09:00:00"
day_end_time = "17:00:00"
timezone = "America/Los_Angeles"

[questions]
file_path = "config/questions.json"
per_day = 10

[features]
show_correct_answer = true
require_work_email = true  # Blocks gmail, yahoo, hotmail, etc.

[s3]
bucket_name = "marathon-trivia-exports"
region = "us-west-2"
```

### Validation at Startup

The application **fails fast** if:
- Questions file is missing or malformed
- TOML configuration is invalid
- Date ranges are inconsistent
- Questions per day don't match configuration

## Workflow-Specific Notes

### PlayerEntityWorkflow

- **Long-running**: Persists for entire event (never completes until event ends)
- **Update handlers**:
  - `start_day(date: str) -> Question`: Begin a day, return first question
  - `submit_answer(date: str, question_id: str, answer_choice: str) -> AnswerResult`
- **Queries**:
  - `get_current_state() -> PlayerState`
  - `get_score_for_day(date: str) -> int`
  - `has_completed_day(date: str) -> bool`
- **Validation**: Prevent answering same question twice, answering days that haven't started/ended, invalid answer choices (must be A/B/C/D)

### DailyWorkflow

- **Started by parent**: EventWorkflow starts at `day_start_time`
- **State**: `player_scores: dict[str, int]`, `completed_players: set[str]`
- **Update handler**: `submit_score(player_id: str, score: int) -> None`
- **Query**: `get_daily_leaderboard() -> list[LeaderboardEntry]`
- **End-of-day**: Signals parent to trigger CSV export

### EventWorkflow

- **Parent workflow**: Manages entire event lifecycle
- **Responsibilities**:
  - Load and validate configuration
  - Schedule timers to start daily child workflows
  - Trigger end-of-day CSV exports to S3
- **Update handler**: `register_player(email, first_name, last_name) -> str` (creates PlayerEntityWorkflow)

## Error Handling

### Validation Rules

- **Email validation**: RFC 5322 format + optional work email check (blocks consumer domains)
- **Duplicate email**: Redirect to existing player (no error)
- **Answer validation**: Must be A/B/C/D, question must exist, day must be active
- **Day boundaries**: Reject submissions before start or after end with configured messages

### Manual Recovery

- **Entity workflow corruption**: Manual recovery required (acceptable for trade show use case)
- **Activity failures**: S3 upload retries 3x with exponential backoff, then logs error

## Git Workflow

- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
- **NEVER use `--no-verify`** when committing (respect pre-commit hooks)
- Keep commits focused and atomic
- Write descriptive commit messages explaining "why", not "what"

## Documentation

- **spec.md**: Complete technical specification (13,000+ words)
- **docs/api/**: Endpoint docs, workflow architecture, data models
- **docs/how-to/**: Setup, deployment, event creation, troubleshooting
- All functions/workflows must have comprehensive docstrings
- File headers: `# ABOUTME: <2-line description of file purpose>`

## Reference Projects

This project reuses patterns from:
- **temporal-trivia-python**: Testing patterns, workflow structure, config patterns
- **durable-wordle**: Entity workflow pattern reference

See these repositories for proven implementations of Temporal Python SDK patterns.
