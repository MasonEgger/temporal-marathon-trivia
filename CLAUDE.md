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

**Python 3.14+ required**. All dependencies managed with `uv`.

### Essential Commands (Currently Implemented)
```bash
just check        # Run all checks: lint + typecheck + test (use before commits)
just test         # Run all tests with pytest and coverage
just test-unit    # Run unit tests only (tests/unit/)
just test-integration  # Run integration tests only (tests/integration/)
just lint         # Run ruff linter on src/ and tests/
just format       # Format code with ruff
just typecheck    # Run mypy --strict on src/

# Run single test file
uv run pytest tests/unit/test_models.py -v

# Run single test case
uv run pytest tests/unit/test_models.py::TestQuestionModel::test_question_with_valid_data_creates_successfully -v

# Install/update dependencies
uv sync               # Install production dependencies
uv sync --extra dev   # Install dev dependencies (required for testing)
```

### Running Services (Future - Not Yet Implemented)
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

### Docker (Future - Not Yet Implemented)
```bash
just build  # Build Docker image
just up     # Start Docker Compose stack
just down   # Stop Docker Compose stack
```

### Data Operations (Future - Not Yet Implemented)
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

- **Unit tests** (`tests/unit/`): Individual workflows, activities, models, API endpoints
- **Integration tests** (`tests/integration/`): Full player journeys, multi-day flows, leaderboard aggregation
- **End-to-end tests**: Complete event lifecycle with time-based transitions
- **Test directories do NOT have `__init__.py`** files (prevents pytest import conflicts)

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
- **Activity failures**: Temporal handles automatic retries - do NOT implement manual retry logic in activities

## Git Workflow

- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
- **NEVER use `--no-verify`** when committing (respect pre-commit hooks)
- Keep commits focused and atomic
- Write descriptive commit messages explaining "why", not "what"

## Implementation Plan

This project follows a strict **35-step TDD implementation plan**:
- **plan.md**: 1,743 lines with detailed RED-GREEN-REFACTOR instructions for each step
- **todo.md**: Progress tracking with checkboxes and completion percentages
- **.ai-sessions/**: Session summaries documenting progress and learnings

**Current Status**: Phase 3 in progress - 15/35 steps complete (42.9% total progress)
- Phase 1 (Project Foundation): 100% complete ✅
- Phase 2 (Configuration and Question Loading): 100% complete ✅
- Phase 3 (Workflow Implementation): 87.5% complete (7/8 steps)

When working on this project:
1. Read the appropriate step in `plan.md` for detailed instructions
2. Follow the numbered sub-instructions exactly (file paths, test scenarios, etc.)
3. Use strict TDD: Write tests first (RED), implement minimally (GREEN), then refactor
4. Update `todo.md` when completing tasks
5. Focus tests on YOUR application logic, not framework behavior
6. **CRITICAL**: Keep all `__init__.py` files EMPTY (Python best practice)

## Documentation

- **spec.md**: Complete technical specification (13,000+ words)
- **plan.md**: 35-step TDD implementation plan with detailed instructions
- **todo.md**: Progress tracking with checkboxes
- **docs/api/**: Endpoint docs, workflow architecture, data models (to be created)
- **docs/how-to/**: Setup, deployment, event creation, troubleshooting (to be created)
- All functions/workflows must have comprehensive docstrings
- File headers: `# ABOUTME: <2-line description of file purpose>`

## Code Style and Best Practices

### Python Module Structure
- **NEVER put anything in `__init__.py` files** - Keep them completely empty
- Use explicit imports: `from src.models.question import Question`
- This prevents import conflicts and makes module structure clearer

### Type Hints and Validation
- Use `mypy --strict` mode - **no `Any` types allowed**
- All functions must have complete type hints
- Pydantic dataclasses for validation (not regular dataclasses)
- Use `@field_validator` for single-field validation
- Use `@model_validator(mode="after")` for cross-field validation
- **Important**: pydantic's `EmailStr` type requires the `email-validator` package (install with `uv add email-validator`)

### Default Values in Dataclasses
- Use `field(default_factory=dict)` for mutable defaults (dict, list, set)
- Use `field(default_factory=set)` for set defaults
- Never use mutable objects as direct default values (e.g., `scores: dict = {}` is WRONG)
- Example:
  ```python
  from dataclasses import dataclass, field

  @dataclass
  class Player:
      daily_scores: dict[str, int] = field(default_factory=dict)
      completed_days: set[str] = field(default_factory=set)
  ```

### File Headers
Every source file must start with:
```python
# ABOUTME: Brief description of file purpose.
# Second line with additional context if needed.
```

### Testing Principles
- Focus on testing YOUR application logic, not framework behavior
- Don't test pydantic validation framework itself
- Don't test that Temporal SDK works correctly
- Test your validation rules, business logic, and data transformations
- Test directories do NOT have `__init__.py` files

## Data Models Implemented (Phase 1 Complete)

### Question Model (`src/models/question.py`)
- Validates A/B/C/D answer format (exactly 4 keys required)
- Validates `correct_answer` is one of A, B, C, or D
- Validates `correct_answer` exists as a key in options dict
- Validates non-empty id and text fields
- 96.88% test coverage (9 test cases)

### Player Model (`src/models/player.py`)
- Email validation using pydantic's `EmailStr` (requires `email-validator` package)
- Display name formatting: `get_display_name()` returns "FirstName L." or just "FirstName" if last_name is empty
- Default values for score tracking: `total_score=0`, `daily_scores={}`, `completed_days=set()`, `current_question_index={}`
- Uses `field(default_factory=...)` for all mutable defaults
- 100% test coverage (10 test cases)

### LeaderboardEntry Model (`src/models/leaderboard.py`)
- Simple dataclass for leaderboard display and "find my rank" functionality
- Fields: rank (int), display_name (str), total_score (int), daily_scores (dict[str, int]), email (str)
- Used for aggregating player performance across all days
- 100% test coverage (3 test cases)

### EventConfig Model (`src/models/config.py`)
- **Workflow-essential fields only** (API/UI fields deferred to Phase 4)
- Date/timing fields: start_date, end_date, day_start_time, day_end_time, timezone
- Questions: questions_file_path, questions_per_day
- Feature flags: show_correct_answer, require_work_email
- S3 export: s3_bucket_name, s3_region
- Three validators:
  - `validate_dates()`: Ensures end_date >= start_date (allows single-day events)
  - `validate_timezone()`: Validates IANA timezone with ZoneInfo
  - `validate_questions_per_day()`: Ensures positive integer (> 0)
- Helper method: `get_all_dates()` returns list[date] from start to end (inclusive)
- 100% test coverage (9 test cases)
- **Design Decision**: API/UI fields (title, description, colors, messages) will be added in Phase 4 when implementing the API layer. This follows TDD principles: only implement what's needed for the current phase.

### Answer Models (`src/models/answer.py`)
- **SubmitAnswerRequest**: Type-safe request model for submit_answer update handler
  - Fields: date (str), question_id (str), answer_choice (str), show_correct_answer (bool)
  - Used to maintain type safety when passing multiple parameters to update handlers
  - Prevents parameter ordering errors and improves refactorability
- **AnswerResult**: Type-safe response model for submit_answer update handler
  - Fields: is_correct (bool), correct_answer (str | None), next_question (Question | None), completion_message (str | None), current_score (int), total_questions (int)
  - Contains all feedback needed by client after answer submission
  - Mutually exclusive next_question and completion_message
- 100% test coverage (6 test cases)
- **Design Pattern**: Request/response dataclasses for complex update handlers ensure type safety

## Temporal Activity Implementation Patterns (CRITICAL)

### Activity Best Practices

**All activities MUST follow these patterns:**

1. **Class-Based Implementation**
   ```python
   class ConfigActivities:
       @activity.defn
       def load_event_config(self, config_path: str) -> EventConfig:
           # Implementation
   ```
   - Activities are implemented as **class methods**, not standalone functions
   - Use `@activity.defn` decorator on the method
   - Benefits: Can share state, inject dependencies, follows Temporal SDK patterns

2. **When to Use `@activity.defn`**
   - **File I/O** (reading, writing)
   - **Network calls** (HTTP, database)
   - **System calls** (time, random)
   - **Any non-deterministic operation**
   - **Reason**: Workflows must be deterministic for replay; activities are not

3. **Synchronous vs Async**
   - **Use `def` (synchronous)** when:
     - Using blocking I/O libraries (`open()`, `tomllib`, etc.)
     - No async version available
     - Simple operations
   - **Use `async def`** when:
     - Using async I/O libraries (`aiofiles`, `httpx`, etc.)
     - Need concurrent operations
     - Long-running operations
   - **File I/O example**: Keep synchronous (blocking I/O)

4. **Testing Activities**
   ```python
   from temporalio.testing import ActivityEnvironment

   activity_env = ActivityEnvironment()
   activities = ConfigActivities()
   result = activity_env.run(activities.load_event_config, config_path)
   ```
   - Use `ActivityEnvironment` for all activity tests
   - Tests run activities synchronously (no Temporal server needed)
   - Can assert on results and exceptions

5. **Error Handling in Activities**
   - Test ALL error paths that could cause workflow failures
   - Missing files, malformed data, validation failures
   - Invalid formats, missing required fields
   - Aim for 95%+ coverage on activities (critical for workflows)

6. **Activity Logging** ⚠️
   ```python
   # CORRECT - activity.logger is a property
   activity.logger.info("Starting operation...")

   # WRONG - Don't call it like a method
   activity.logger().info("message")  # This will fail!
   ```
   - Use `activity.logger` (property) not `activity.logger()` (method)
   - Logs integrate with Temporal's observability system
   - Visible in Temporal UI for debugging

7. **Automatic Retry Handling** ⚠️
   ```python
   # WRONG - Do NOT add manual retry logic
   for attempt in range(3):
       try:
           s3_client.put_object(...)
       except:
           time.sleep(2**attempt)  # Bad!

   # CORRECT - Let Temporal handle retries
   s3_client.put_object(...)  # Temporal retries on failure
   ```
   - **Temporal automatically retries activities** based on retry policy
   - Manual retry logic defeats the purpose of using Temporal
   - Configure retry policies at workflow level when calling activities
   - Trust the framework - this is a core Temporal feature

### Activity Implementation Checklist

Before implementing an activity, ask:
- [ ] Does this operation involve I/O? → Use `@activity.defn`
- [ ] Is the I/O blocking? → Keep synchronous (`def`)
- [ ] Is the I/O async-friendly? → Use async (`async def`)
- [ ] Implement as class-based pattern with methods
- [ ] Test with `ActivityEnvironment`
- [ ] Cover all error paths that could fail workflows

### Example: ConfigActivities

```python
# src/activities/config.py
class ConfigActivities:
    """Activity class for configuration-related operations."""

    @activity.defn
    def load_event_config(self, config_path: str) -> EventConfig:
        """Load TOML config (synchronous - blocking file I/O)."""
        # Implementation with comprehensive error handling
```

```python
# tests/unit/test_activities.py
def test_load_event_config():
    activity_env = ActivityEnvironment()
    activities = ConfigActivities()
    result = activity_env.run(activities.load_event_config, "path/to/config.toml")
    assert isinstance(result, EventConfig)
```

## Activities Implemented (Phase 2: 100% Complete)

### ConfigActivities (`src/activities/config.py`)
- **Method**: `load_event_config(config_path: str) -> EventConfig`
- **Pattern**: Synchronous (blocking file I/O with `tomllib`)
- **Error handling**: FileNotFoundError, ValueError for malformed TOML, missing sections, invalid date/time formats
- **Testing**: 13 comprehensive tests using `ActivityEnvironment`
- **Coverage**: 95.92% (only missing generic exception handler)

### QuestionsActivities (`src/activities/questions.py`)
- **Methods**:
  - `load_questions(file_path: str) -> dict[str, list[Question]]` - Load and parse all questions from JSON
  - `get_questions_for_day(file_path: str, date: str) -> list[Question]` - Get questions for specific date
  - `validate_questions_file(file_path: str, config: EventConfig) -> None` - Validate questions against config
- **Pattern**: Synchronous (blocking file I/O with `json`)
- **Error handling**: FileNotFoundError, ValueError for malformed JSON, KeyError for invalid dates, validation failures
- **Testing**: 12 comprehensive tests using `ActivityEnvironment`
- **Coverage**: 100% (41 statements, 0 missed)
- **Key Design**: Leverages Question model's pydantic validation for A/B/C/D and correct_answer checks

### EmailActivities (`src/activities/email.py`)
- **Method**: `validate_email(email: str, require_work_email: bool) -> bool`
- **Pattern**: Synchronous (pure logic, no I/O - just regex and string operations)
- **Email validation**: RFC 5322 format checking via regex pattern
- **Consumer domain blocking**: Blocks gmail, yahoo, hotmail, outlook, aol, icloud when `require_work_email=True`
- **Case-insensitive**: Domain checking uses `.lower()` for case-insensitive comparison
- **Error handling**: Graceful handling of empty strings and malformed emails (returns False)
- **Testing**: 10 comprehensive tests using `ActivityEnvironment`
- **Coverage**: 88.89% (18 statements, 2 missed - only generic exception handler)
- **Key Design**: Returns bool (True if valid, False otherwise) rather than raising exceptions

### ExportActivities (`src/activities/export.py`)
- **Method**: `export_daily_csv_to_s3(bucket: str, region: str, date: str, players: list[Player], event_dates: list[str]) -> str`
- **Pattern**: Synchronous (blocking I/O with `boto3`)
- **CSV generation**: In-memory CSV using `io.StringIO` with dynamic day columns
- **S3 upload**: Uses boto3 client to upload CSV to S3
- **Logging**: Uses `activity.logger` (property) for Temporal-integrated logging
- **Retry handling**: Lets Temporal handle retries automatically (no manual retry logic)
- **Error handling**: Raises exceptions on failure, Temporal retries as configured
- **Testing**: 7 unit tests + 1 integration test using `ActivityEnvironment` and `moto` for S3 mocking
- **Coverage**: 100% (30 statements, 0 missed)
- **Key Design**:
  - Returns S3 URL for logging/tracking
  - Dynamic day columns based on event_dates parameter
  - Works with moto for reliable testing without AWS credentials

## Temporal Workflow Implementation Patterns (CRITICAL)

### Workflow Best Practices

**All workflows MUST follow these patterns:**

1. **Entity Workflow Pattern** 🔑
   ```python
   @workflow.defn
   class PlayerEntityWorkflow:
       def __init__(self) -> None:
           self.state: PlayerState | None = None

       @workflow.run
       async def run(self, player_id: str, email: str, first_name: str, last_name: str) -> None:
           # Initialize state
           self.state = PlayerState(player=Player(...))
           # Keep running indefinitely
           await workflow.wait_condition(lambda: False)
   ```
   - Entity workflows run indefinitely for entire business process duration
   - Use `workflow.wait_condition(lambda: False)` to keep alive
   - State persists in workflow instance (self.state)
   - Respond to queries and update handlers while running
   - Perfect for per-user, per-game, per-order scenarios

2. **Workflow Queries** 🔑
   ```python
   @workflow.query
   def get_current_state(self) -> PlayerState:
       if self.state is None:
           raise RuntimeError("Workflow state not initialized")
       # CRITICAL: Return defensive copy to prevent external mutation
       return PlayerState(
           player=Player(
               id=self.state.player.id,
               email=self.state.player.email,
               # ... copy all fields
               daily_scores=dict(self.state.player.daily_scores),
               completed_days=set(self.state.player.completed_days),
           ),
           current_day=self.state.current_day,
           current_question_index=self.state.current_question_index,
       )
   ```
   - Queries are read-only operations
   - **ALWAYS return defensive copies** (never return self.state directly)
   - Use `dict()`, `set()` for mutable collections
   - Can be called even after workflow completes
   - Always validate state is initialized

3. **Pydantic Data Converter** 🔑
   ```python
   # Required when using pydantic models (EmailStr, BaseModel, etc.)
   from temporalio.client import Client
   from temporalio.contrib.pydantic import pydantic_data_converter

   # In tests
   async with await WorkflowEnvironment.start_time_skipping() as env:
       # Configure client with pydantic converter
       new_config = env.client.config()
       new_config["data_converter"] = pydantic_data_converter
       client = Client(**new_config)

       async with Worker(client, task_queue="test-queue", workflows=[MyWorkflow]):
           handle = await client.start_workflow(...)
   ```
   - **Required** for serializing pydantic models in workflows
   - Handles EmailStr, BaseModel, and other pydantic types
   - Configure per-client (not global)
   - Must be used consistently (worker and client)
   - Without this, you'll get: `TypeError: Unserializable type during conversion`

4. **Workflow Testing with WorkflowEnvironment** 🔑
   ```python
   from temporalio.testing import WorkflowEnvironment
   from temporalio.worker import Worker
   import concurrent.futures

   async with await WorkflowEnvironment.start_time_skipping() as env:
       # Configure client with pydantic converter
       new_config = env.client.config()
       new_config["data_converter"] = pydantic_data_converter
       client = Client(**new_config)

       # CRITICAL: Use ThreadPoolExecutor for synchronous activities
       with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
           async with Worker(
               client,
               task_queue="test-queue",
               workflows=[MyWorkflow],
               activities=[mock_activities.some_activity],
               activity_executor=activity_executor,  # Required for sync activities!
           ):
               handle = await client.start_workflow(
                   MyWorkflow.run,
                   args=["arg1", "arg2"],
                   id=f"test-workflow-{uuid.uuid4()}",
                   task_queue="test-queue",
               )

               # CRITICAL: Allow workflow to initialize state before calling updates
               await asyncio.sleep(0.1)

               # Now safe to call updates/queries
               result = await handle.query(MyWorkflow.my_query)
   ```
   - Use `WorkflowEnvironment.start_time_skipping()` for unit tests
   - **CRITICAL**: Add `ThreadPoolExecutor` with `activity_executor` parameter for sync activities
   - Without executor: "Activity X is not async so an activity_executor must be present" error
   - Use `max_workers=100` for concurrent operations (e.g., multiple player registrations)
   - **CRITICAL**: Add `await asyncio.sleep(0.1)` after starting workflow before calling updates
   - Without sleep: "Workflow state not initialized" RuntimeError
   - Allows time control for testing time-dependent logic
   - Clean async context managers for setup/teardown
   - Worker must be running to execute workflow
   - Always use unique workflow IDs in tests

5. **Data Model Placement** 🔑
   - **Place in `src/models/`** if:
     - Used by multiple workflows/activities
     - Represents business data (Player, Question, Config)
     - Has validation logic
     - Needs to be serialized across workflow boundaries
   - **Workflow state models**: All workflow state models are consolidated in `src/models/state.py`
     - PlayerState (for PlayerEntityWorkflow)
     - DailyState (for DailyWorkflow)
     - EventState (future - for EventWorkflow)
   - **Rationale**: Clean separation of concerns, reusable data structures, single source of truth

### Workflow Testing Checklist

Before writing a workflow test:
- [ ] Import pydantic_data_converter from temporalio.contrib.pydantic
- [ ] Configure client with pydantic converter in test setup
- [ ] Use WorkflowEnvironment.start_time_skipping() for unit tests
- [ ] Generate unique workflow IDs with uuid.uuid4()
- [ ] Test queries return correct data types
- [ ] Test state initialization (zero scores, empty sets)
- [ ] Mock activities if workflow calls them (future steps)

### Common Workflow Errors and Solutions

1. **EmailStr Serialization Error**
   - **Error**: `TypeError: Unserializable type during conversion: <class 'pydantic.networks.EmailStr'>`
   - **Solution**: Configure client with `pydantic_data_converter`
   - **Where**: In test setup before creating Worker

2. **State Not Initialized**
   - **Error**: Queries fail or return None
   - **Solution**: Always check `if self.state is None` in queries
   - **Pattern**: Raise RuntimeError with clear message

3. **External State Mutation**
   - **Error**: Workflow state gets modified externally
   - **Solution**: Return defensive copies from queries
   - **Pattern**: Use `dict()`, `set()` to copy mutable collections

## Workflows Implemented (Phase 3: 87.5% Complete)

### PlayerEntityWorkflow (`src/workflows/player.py`)
- **Status**: COMPLETE - All core functionality implemented (Steps 9-11) ✅
- **Pattern**: Entity workflow (runs indefinitely)
- **State**: PlayerState with Player model + current_day + current_question_index + current_questions
- **Run method**: Initializes state, runs indefinitely with `workflow.wait_condition(lambda: False)`
- **Queries implemented**:
  - `get_current_state() -> PlayerState` - Returns defensive copy of state
  - `get_score_for_day(date: str) -> int` - Returns score for specific day (0 if unplayed)
  - `has_completed_day(date: str) -> bool` - Checks if day is completed
- **Update handlers implemented**:
  - `start_day(date: str, file_path: str = "config/questions.json") -> Question` - Loads questions via activity, returns first question
  - `submit_answer(request: SubmitAnswerRequest) -> AnswerResult` - Validates answer, updates score, returns next question or completion
- **Helper methods**:
  - `_get_current_question() -> Question` - Returns current question with validation
  - `_is_answer_correct(question: Question, answer: str) -> bool` - Checks answer correctness
- **Testing**: 21 comprehensive tests with pydantic_data_converter and activity mocking
- **Coverage**: 89.16% (83 statements, 9 missed)

### DailyWorkflow (`src/workflows/daily.py`)
- **Status**: COMPLETE - Leaderboard ranking implemented (Steps 12-13) ✅
- **Pattern**: Entity workflow (runs indefinitely for one day)
- **State**: DailyState with date, questions, player_scores, completed_players, player_info, config
- **Run method**: Initializes state, runs indefinitely with `workflow.wait_condition(lambda: False)`
- **Queries implemented**:
  - `get_daily_leaderboard() -> list[LeaderboardEntry]` - Returns ranked leaderboard with tie handling and alphabetical sorting
  - `is_day_active() -> bool` - Time-based check using `workflow.now()`
- **Update handlers implemented**:
  - `submit_score(request: SubmitScoreRequest) -> None` - Stores player score and marks as completed
  - `validate_submit_score(request: SubmitScoreRequest) -> None` - Validator preventing duplicate submissions
- **Helper functions**:
  - `calculate_leaderboard(player_scores, player_info) -> list[LeaderboardEntry]` - Ranking algorithm with tie handling
- **Testing**: 11 comprehensive tests with pydantic_data_converter (6 basic + 5 leaderboard ranking)
- **Coverage**: 91.80% (61 statements, 5 missed)
- **Key Features**:
  - Tied players share same rank (5 at rank 1 → next is rank 6)
  - Alphabetical tie-breaking by last name, then first name
  - Display names in "FirstName L." format
  - Temporal update validator prevents duplicate score submissions

### EventWorkflow (`src/workflows/event.py`)
- **Status**: PLAYER REGISTRATION COMPLETE (Steps 14-15) ✅
- **Pattern**: Parent workflow (manages entire event)
- **State**: EventState with event_id, config, daily_workflow_ids, player_count, player_registry
- **Run method**: Loads config via activity, validates questions via activity, initializes state, runs indefinitely
- **Queries implemented**:
  - `get_event_status() -> dict` - Returns event_id and player_count for monitoring
  - `get_player_id_by_email(email: str) -> str | None` - Lookup player by email
- **Update handlers implemented**:
  - `register_player(request: RegisterPlayerRequest) -> str` - Creates PlayerEntityWorkflow child, validates email, handles duplicates
- **Activities called**:
  - `load_event_config(config_path)` - Loads TOML configuration
  - `validate_questions_file(file_path, config)` - Validates questions match config
  - `validate_email(email, require_work_email)` - Validates email format and work domain
- **Testing**: 11 comprehensive tests with pydantic_data_converter, mock activities, and ThreadPoolExecutor
- **Coverage**: 91.30% (44 statements, 4 missed)
- **Key Features**:
  - Configuration loading at workflow startup (fail fast on errors)
  - Player registration with child workflow creation
  - Email validation and duplicate detection
  - Player registry for email → player_id mapping
  - Activity method references for type safety (not string-based)
  - Parent workflow pattern for event coordination

### Workflow State Models (`src/models/state.py`)
- **Purpose**: Consolidated file for all workflow state dataclasses
- **PlayerState**: Workflow state for PlayerEntityWorkflow
  - Fields: player (Player), current_day (str | None), current_question_index (int), current_questions (list[Question] | None)
  - Design: Combines business data with workflow-specific state. Stores only current day's questions (not all days) for efficiency.
- **DailyState**: Workflow state for DailyWorkflow
  - Fields: date (str), questions (list[Question]), player_scores (dict[str, int]), completed_players (set[str]), player_info (dict[str, tuple[str, str, str]]), config (EventConfig | None)
  - Design: Manages daily leaderboard state with player scores, completion tracking, and player identity for ranking
- **EventState**: Workflow state for EventWorkflow
  - Fields: event_id (str), config (EventConfig), daily_workflow_ids (dict[str, str]), player_count (int), player_registry (dict[str, str])
  - Design: Manages entire event lifecycle with child workflow tracking and player registry for duplicate detection
- **Coverage**: 100% (20 statements, 0 missed)
- **Design Pattern**: All workflow state models consolidated in single file for better organization

## Reference Projects

This project reuses patterns from:
- **samples-python** (`/Users/masonegger/Code/Temporal/samples-python/`): Official Temporal Python SDK examples
  - `tests/hello/` - Query and update handler patterns
  - `pydantic_converter/` - Pydantic data converter usage
  - `tests/conftest.py` - WorkflowEnvironment fixture patterns
- **temporal-trivia-python**: Testing patterns, workflow structure, config patterns
- **durable-wordle**: Entity workflow pattern reference

**CRITICAL**: Always check samples-python when implementing new Temporal features (queries, updates, child workflows, etc.)

### Update Handler Patterns (Steps 10+) 🔑

1. **Calling Activities from Workflows** ⚠️
   ```python
   # WRONG - String-based (not type-safe, breaks on refactoring)
   result = await workflow.execute_activity(
       "get_questions_for_day",
       args=[file_path, date],
       start_to_close_timeout=timedelta(seconds=10),
   )

   # CORRECT - Method reference (type-safe, refactorable, IDE support)
   from src.activities.questions import QuestionsActivities

   questions_activities = QuestionsActivities()
   result = await workflow.execute_activity_method(
       questions_activities.get_questions_for_day,
       args=[file_path, date],
       start_to_close_timeout=timedelta(seconds=10),
   )
   ```
   - **NEVER** call activities using string names
   - **ALWAYS** import activity class, create instance, pass method reference
   - Benefits: type safety, IDE autocomplete, refactoring support, compile-time errors
   - Use `workflow.execute_activity_method()` not `workflow.execute_activity()`

2. **Update Handlers vs Queries vs Signals**
   ```python
   @workflow.update
   async def start_day(self, date: str) -> Question:
       """Update handler - modifies state AND returns value immediately."""
       # Validation
       if self.state is None:
           raise RuntimeError("Workflow state not initialized")
       # Modify state
       self.state.current_day = date
       # Return value
       return first_question
   ```
   - **Queries**: Read-only, `@workflow.query`, return data
   - **Updates**: Modify state, `@workflow.update`, return value immediately
   - **Signals**: Modify state, `@workflow.signal`, no return value
   - Use updates when you need to modify state AND return a result

3. **Activity Mocking in Workflow Tests**
   ```python
   class MockQuestionsActivities:
       @activity.defn(name="get_questions_for_day")
       async def get_questions_for_day(self, file_path: str, date: str) -> list[Question]:
           return [Question(...), Question(...)]

   # In test
   mock_activities = MockQuestionsActivities()
   async with Worker(
       client,
       task_queue="test-queue",
       workflows=[PlayerEntityWorkflow],
       activities=[mock_activities.get_questions_for_day],
   ):
       handle = await client.start_workflow(...)
       result = await handle.execute_update(PlayerEntityWorkflow.start_day, "2025-03-10")
   ```
   - Use `@activity.defn(name="actual_activity_name")` to mock activities
   - Return test data without actual I/O
   - Pass mock methods to Worker's activities list

4. **Efficient State Storage**
   - Store only what's needed for current operations
   - Example: `current_questions: list[Question] | None` (current day only)
   - NOT: `questions: dict[str, list[Question]]` (all days - wasteful!)
   - Reduces memory per workflow, prevents duplication
   - Think about scale: 1000 players × 50 questions vs 1000 players × 5 questions

5. **Update Handler Exception Handling** 🔑🔑🔑 **CRITICAL**
   ```python
   from temporalio.exceptions import ApplicationError

   # WRONG - Causes infinite retries and hung tests
   @workflow.update
   def submit_answer(self, request: SubmitAnswerRequest) -> AnswerResult:
       if request.answer_choice not in ["A", "B", "C", "D"]:
           raise ValueError("Invalid answer_choice")  # BAD! Infinite retries!

   # CORRECT - Proper error propagation to client
   @workflow.update
   def submit_answer(self, request: SubmitAnswerRequest) -> AnswerResult:
       if request.answer_choice not in ["A", "B", "C", "D"]:
           raise ApplicationError("Invalid answer_choice")  # GOOD!
   ```
   - **MUST use `ApplicationError`** for all validation failures in update handlers
   - **Other exceptions** (ValueError, TypeError, etc.) cause infinite retries
   - Workflow gets stuck retrying, tests hang indefinitely
   - From samples-python: "Other exceptions will cause the workflow to keep retrying and get it stuck"
   - **This is the #1 gotcha for update handlers**

6. **Testing Update Handler Exceptions** 🔑
   ```python
   from temporalio.client import WorkflowUpdateFailedError

   # Test pattern for update handler errors
   with pytest.raises(WorkflowUpdateFailedError) as exc_info:
       await handle.execute_update(
           PlayerEntityWorkflow.submit_answer,
           SubmitAnswerRequest("2025-03-10", "q1", "E", False),  # Invalid answer
       )
   # Check the CAUSE, not the exception message
   assert "answer_choice" in str(exc_info.value.cause).lower()
   ```
   - Use `WorkflowUpdateFailedError` from temporalio.client
   - Check `exc_info.value.cause` for underlying ApplicationError
   - Pattern from samples-python safe_message_handlers
   - Do NOT use `pytest.raises(Exception)` or check `exc_info.value` directly

7. **Temporal Update Validators** 🔑🔑 **CRITICAL**
   ```python
   # Validators prevent bad updates from being written to workflow history
   @workflow.update
   def submit_score(self, request: SubmitScoreRequest) -> None:
       """Update handler mutates state - assumes validator passed."""
       # No need for defensive state checks - validator ensures preconditions
       self.state.player_scores[request.player_id] = request.score
       self.state.completed_players.add(request.player_id)

   @submit_score.validator
   def validate_submit_score(self, request: SubmitScoreRequest) -> None:
       """Validator checks preconditions before update is written to history."""
       if self.state is None:
           raise ValueError("Workflow state not initialized")
       if request.player_id in self.state.completed_players:
           raise ValueError(f"Player already submitted score")
       # Raise ANY exception to reject - not just ApplicationError
   ```
   - **Use `@<update_name>.validator` decorator** to validate before execution
   - Validators run BEFORE update is written to workflow event history
   - Raise **any exception** to reject (ValueError, RuntimeError, etc. - not just ApplicationError)
   - If validator passes, update handler executes and mutates state
   - **Benefits**: Clean separation (validation vs mutation), prevents bad updates from polluting history
   - **When to use**: Checking preconditions, detecting duplicates, validating business rules
   - **Update handler**: Can skip redundant checks since validator guarantees preconditions
   - Docs: https://docs.temporal.io/develop/python/message-passing#updates

8. **Type-Safe Request/Response Models** 🔑
   ```python
   # src/models/answer.py
   @dataclass
   class SubmitAnswerRequest:
       """Request model for type-safe update handler parameters."""
       date: str
       question_id: str
       answer_choice: str
       show_correct_answer: bool

   @dataclass
   class AnswerResult:
       """Response model for type-safe update handler returns."""
       is_correct: bool
       correct_answer: str | None
       next_question: Question | None
       completion_message: str | None
       current_score: int
       total_questions: int

   # Usage in workflow
   @workflow.update
   def submit_answer(self, request: SubmitAnswerRequest) -> AnswerResult:
       # Type-safe access to all fields
       if request.answer_choice not in ["A", "B", "C", "D"]:
           raise ApplicationError("Invalid answer")
       return AnswerResult(...)
   ```
   - Multi-parameter update handlers → create request dataclass
   - Complex return values → create response dataclass
   - Both belong in `src/models/` (not in workflow file)
   - Benefits: type safety, refactorability, clear API contracts

8. **Update Handlers: Synchronous vs Asynchronous** 🔑
   ```python
   # Synchronous (no activities) - use def
   @workflow.update
   def submit_answer(self, request: SubmitAnswerRequest) -> AnswerResult:
       is_correct = request.answer == question.correct_answer
       return AnswerResult(is_correct=is_correct)

   # Asynchronous (calls activities) - use async def
   @workflow.update
   async def start_day(self, date: str) -> Question:
       questions = await workflow.execute_activity_method(...)
       return questions[0]
   ```
   - Use `def` for pure validation/scoring logic
   - Use `async def` only when calling activities or child workflows
   - Match sync/async to whether you await operations
   - Using `async def` without await can cause tests to hang

9. **Time-Based Workflow Logic** 🔑
   ```python
   @workflow.query
   def is_day_active(self) -> bool:
       # Use workflow.now() for deterministic time
       current_time = workflow.now()
       current_time_of_day = current_time.time()

       # Compare with configured bounds
       day_start = self.state.config.day_start_time
       day_end = self.state.config.day_end_time
       return day_start <= current_time_of_day <= day_end
   ```
   - **ALWAYS use `workflow.now()`** not `datetime.now()` for determinism
   - Extract time component with `.time()` for time-of-day comparisons
   - Enables proper replay and testing with time-skipping
   - Critical for time-based access control in DailyWorkflow

10. **Child Workflow Creation** 🔑🔑🔑 **CRITICAL**
    ```python
    # WRONG - workflow.uuid4() returns UUID object
    player_id = workflow.uuid4()
    await workflow.start_child_workflow(..., id=player_id)  # TypeError!

    # CORRECT - Convert UUID to string
    player_id = str(workflow.uuid4())
    await workflow.start_child_workflow(
        PlayerEntityWorkflow.run,
        args=[player_id, email, first_name, last_name],
        id=player_id,  # Must be string!
        task_queue=workflow.info().task_queue,
    )
    ```
    - **workflow.uuid4() returns UUID object, NOT string** - ALWAYS convert with `str()`
    - Failure mode: TypeError "bad argument type for built-in operation"
    - Manifests as hanging test with retries
    - **Await `start_child_workflow()` to initiate**, but don't await the handle for indefinite workflows
    - Child workflow ID must be string for idempotency
    - Use `workflow.info().task_queue` to use same queue as parent
    - From Step 15: This is the #1 gotcha for child workflow creation

11. **ThreadPoolExecutor for Synchronous Activities in Tests** 🔑🔑 **CRITICAL**
    ```python
    import concurrent.futures

    # When testing workflows that call synchronous activities
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        async with Worker(
            client,
            task_queue="test-queue",
            workflows=[EventWorkflow, PlayerEntityWorkflow],
            activities=[
                mock_config_activities.load_event_config,  # async
                mock_email_activities.validate_email,  # async mock of sync real
            ],
            activity_executor=activity_executor,  # REQUIRED!
        ):
            # Test code
    ```
    - **REQUIRED when ANY activity is synchronous** (even if mock is async)
    - Error without it: "Activity X is not async so an activity_executor must be present"
    - Use `max_workers=100` for concurrent player registration scenarios
    - Wrap Worker creation with ThreadPoolExecutor context manager
    - Mock activities can be async for test simplicity, but executor still needed
    - From Step 15: This pattern required for ALL tests with sync activities

12. **Workflow Initialization Timing in Tests** 🔑🔑 **CRITICAL**
    ```python
    handle = await client.start_workflow(
        EventWorkflow.run,
        args=["event-id", "config/event.toml"],
        id=f"test-workflow-{uuid.uuid4()}",
        task_queue="test-queue",
    )

    # CRITICAL: Allow workflow run method to initialize self.state
    await asyncio.sleep(0.1)

    # Now safe to call update handlers
    result = await handle.execute_update(
        EventWorkflow.register_player,
        RegisterPlayerRequest(...)
    )
    ```
    - Workflow run method initializes `self.state` asynchronously
    - Update handlers check `if self.state is None: raise RuntimeError(...)`
    - Without sleep: "Workflow state not initialized" RuntimeError with infinite retries
    - 0.1 seconds sufficient for test environment
    - **Required for ALL update handlers on newly started workflows**
    - From Step 15: Critical pattern discovered through debugging hanging tests