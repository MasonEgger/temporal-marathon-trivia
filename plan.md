# Marathon Trivia Platform - Implementation Plan

**Version**: 1.0
**Date**: 2025-11-25
**Status**: Planning Complete - Ready for Implementation

## Current Status

- [x] Specification complete (spec.md)
- [ ] Project structure and dependencies
- [ ] Core data models
- [ ] Configuration system
- [ ] Activity implementations
- [ ] Workflow implementations
- [ ] API layer
- [ ] Frontend templates
- [ ] Deployment configuration
- [ ] Documentation

## Implementation Philosophy

This plan follows strict TDD (Test-Driven Development) principles:
1. **RED**: Write failing tests that define desired behavior
2. **GREEN**: Write minimal code to make tests pass
3. **REFACTOR**: Improve code while keeping tests green

Each step builds incrementally on previous work with no orphaned code. All tests focus on **application logic only**, not framework behavior.

---

## Phase 1: Project Foundation

### Step 1: Project Structure and Dependencies

**Goal**: Set up the basic project structure, dependency management, and development tooling.

```text
Set up the Marathon Trivia project foundation with proper Python tooling and project structure.

1. Create project structure:
   - Create src/ directory with __init__.py
   - Create src/models/ directory with __init__.py
   - Create src/workflows/ directory with __init__.py
   - Create src/activities/ directory with __init__.py
   - Create src/api/ directory with __init__.py
   - Create config/ directory
   - Create frontend/ directory
   - Create frontend/templates/ directory
   - Create frontend/static/ directory
   - Create docs/ directory
   - Create docs/api/ directory
   - Create docs/how-to/ directory

2. Create pyproject.toml:
   - Set project name: "temporal-marathon-trivia"
   - Set Python version requirement: ">=3.14"
   - Add dependencies:
     - temporalio (latest)
     - fastapi (latest)
     - uvicorn[standard] (latest)
     - redis (latest)
     - pydantic (for validation)
     - jinja2 (for templates)
     - httpx (for testing)
     - boto3 (for S3)
     - python-multipart (for form handling)
   - Add dev dependencies:
     - pytest
     - pytest-asyncio
     - pytest-cov
     - mypy
     - ruff
     - fakeredis[lua]
     - moto[s3]
     - nox
   - Configure ruff with strict settings
   - Configure mypy with strict mode
   - Configure pytest with asyncio mode and coverage settings

3. Create Justfile with initial tasks:
   - test: Run pytest with coverage
   - test-unit: Run unit tests only
   - test-integration: Run integration tests only
   - lint: Run ruff check
   - format: Run ruff format
   - typecheck: Run mypy --strict on src/
   - check: Run lint, typecheck, and test in sequence

4. Create .gitignore:
   - Standard Python ignores (__pycache__, .pytest_cache, .mypy_cache)
   - Virtual environment directories (.venv, venv)
   - Coverage reports (.coverage, htmlcov/)
   - IDE files (.vscode/, .idea/)
   - Environment files (.env)
   - Build artifacts (dist/, build/, *.egg-info)

5. Create .env.example:
   - TEMPORAL_ADDRESS=localhost:7233
   - TEMPORAL_NAMESPACE=default
   - TEMPORAL_TASK_QUEUE=marathon-trivia
   - REDIS_URL=redis://localhost:6379
   - API_HOST=0.0.0.0
   - API_PORT=8000
   - AWS_ACCESS_KEY_ID=your_key_here
   - AWS_SECRET_ACCESS_KEY=your_secret_here

6. Initialize uv lock file:
   - Run: uv sync

7. Verify setup:
   - Run: just check (should pass with no code yet)
   - Confirm all directories exist
   - Confirm pyproject.toml is valid
```

---

### Step 2: Core Data Models - Question

**Goal**: Implement the Question dataclass with validation and tests.

**NOTE**: This is the first actual code implementation. Focus on application-specific validation logic.

```text
Implement the Question data model with comprehensive validation of the A/B/C/D answer format.

1. RED: Write Question model tests first:
   - Create tests/unit/test_models.py:
     - Test that Question with valid data (id, text, 4 options A/B/C/D, correct_answer="A") creates successfully
     - Test that Question.options must have exactly keys ["A", "B", "C", "D"]
     - Test that Question.options with missing key "D" raises validation error
     - Test that Question.options with extra key "E" raises validation error
     - Test that Question.correct_answer must be one of ["A", "B", "C", "D"]
     - Test that Question.correct_answer="E" raises validation error
     - Test that Question.correct_answer must match a key in options dict
     - Test that empty question text raises validation error
     - Test that empty question id raises validation error

2. GREEN: Implement Question model minimally:
   - Create src/models/question.py:
     - Add file header: "# ABOUTME: Question data model for multiple choice trivia questions.\n# Validates A/B/C/D answer format and correct answer selection."
     - Import dataclass, field from dataclasses
     - Import model_validator from pydantic.dataclasses
     - Use @pydantic.dataclasses.dataclass decorator for validation
     - Define Question with fields: id (str), text (str), options (dict[str, str]), correct_answer (str)
     - Add @model_validator(mode='after') method validate_options:
       - Check options has exactly keys {"A", "B", "C", "D"}
       - Raise ValueError if not
     - Add @model_validator(mode='after') method validate_correct_answer:
       - Check correct_answer is in ["A", "B", "C", "D"]
       - Check correct_answer is a key in options
       - Raise ValueError if not
     - Add @model_validator(mode='after') method validate_non_empty:
       - Check id and text are non-empty strings
       - Raise ValueError if empty
     - Add comprehensive docstring explaining validation rules

3. Update src/models/__init__.py:
   - Export Question class

4. REFACTOR: Improve validation error messages:
   - Make error messages user-friendly and specific
   - Add examples to docstrings

5. Verify tests pass and run just check
```

---

### Step 3: Core Data Models - Player

**Goal**: Implement the Player dataclass with display name formatting logic.

```text
Implement the Player data model with display name formatting (FirstName L.).

1. RED: Write Player model tests first:
   - Add to tests/unit/test_models.py:
     - Test that Player with valid data creates successfully
     - Test that Player.get_display_name() returns "FirstName L." format
     - Test that Player.get_display_name() with first_name="John", last_name="Doe" returns "John D."
     - Test that Player.get_display_name() with last_name="" returns just first_name
     - Test that Player.total_score starts at 0 by default
     - Test that Player.daily_scores is empty dict by default
     - Test that Player.completed_days is empty set by default
     - Test that Player.current_question_index is empty dict by default
     - Test that Player.email validation requires valid email format
     - Test that invalid email raises validation error

2. GREEN: Implement Player model minimally:
   - Create src/models/player.py:
     - Add file header: "# ABOUTME: Player data model representing player state and identity.\n# Includes display name formatting and score tracking across multiple days."
     - Import dataclass, field from dataclasses
     - Import EmailStr from pydantic
     - Use @pydantic.dataclasses.dataclass decorator
     - Define Player with fields:
       - id: str
       - email: EmailStr
       - first_name: str
       - last_name: str
       - total_score: int = 0
       - daily_scores: dict[str, int] = field(default_factory=dict)
       - completed_days: set[str] = field(default_factory=set)
       - current_question_index: dict[str, int] = field(default_factory=dict)
     - Add method get_display_name() -> str:
       - Return f"{self.first_name} {self.last_name[0]}." if last_name exists
       - Return self.first_name if last_name is empty
     - Add comprehensive docstring

3. Update src/models/__init__.py:
   - Export Player class

4. REFACTOR: Add helper methods if needed:
   - Consider add_daily_score(date: str, score: int) method
   - Consider mark_day_completed(date: str) method

5. Verify tests pass and run just check
```

---

### Step 4: Core Data Models - LeaderboardEntry and EventConfig

**Goal**: Complete the core data models needed for the application.

```text
Implement LeaderboardEntry and EventConfig data models.

1. RED: Write LeaderboardEntry tests first:
   - Add to tests/unit/test_models.py:
     - Test that LeaderboardEntry with valid data creates successfully
     - Test that LeaderboardEntry fields are correctly typed (rank: int, display_name: str, total_score: int, daily_scores: dict, email: str)
     - Test that LeaderboardEntry can be created with empty daily_scores dict

2. GREEN: Implement LeaderboardEntry model minimally:
   - Create src/models/leaderboard.py:
     - Add file header: "# ABOUTME: Leaderboard entry model for displaying player rankings.\n# Used for leaderboard display and 'find my rank' functionality."
     - Import dataclass, field from dataclasses
     - Use @pydantic.dataclasses.dataclass decorator
     - Define LeaderboardEntry with fields:
       - rank: int
       - display_name: str
       - total_score: int
       - daily_scores: dict[str, int]
       - email: str
     - Add comprehensive docstring

3. RED: Write EventConfig tests first:
   - Add to tests/unit/test_models.py:
     - Test that EventConfig with all required fields creates successfully
     - Test that EventConfig date validation ensures end_date > start_date
     - Test that EventConfig with end_date < start_date raises validation error
     - Test that EventConfig validates timezone is valid
     - Test that EventConfig validates color format (hex colors like "#3b82f6")
     - Test that EventConfig.questions_per_day must be positive integer

4. GREEN: Implement EventConfig model minimally:
   - Create src/models/config.py:
     - Add file header: "# ABOUTME: Event configuration model loaded from TOML files.\n# Validates dates, times, colors, and feature flags for trivia events."
     - Import dataclass from dataclasses
     - Import date, time from datetime
     - Import ZoneInfo from zoneinfo
     - Use @pydantic.dataclasses.dataclass decorator
     - Define EventConfig with all fields from spec section 3.4:
       - Event metadata: title, description, base_url
       - Dates/timing: start_date, end_date, day_start_time, day_end_time, timezone
       - Questions: questions_file_path, questions_per_day
       - UI messages: completion_message, day_over_message, not_started_message, already_completed_message
       - Colors: primary_color, secondary_color, background_color, text_color
       - Feature flags: show_correct_answer, require_work_email
       - S3: s3_bucket_name, s3_region
     - Add @model_validator(mode='after') method validate_dates:
       - Check end_date > start_date
       - Raise ValueError if not
     - Add @model_validator(mode='after') method validate_timezone:
       - Try to create ZoneInfo(timezone)
       - Raise ValueError if invalid
     - Add @model_validator(mode='after') method validate_questions_per_day:
       - Check questions_per_day > 0
       - Raise ValueError if not
     - Add comprehensive docstring

5. Update src/models/__init__.py:
   - Export LeaderboardEntry and EventConfig classes

6. REFACTOR: Add helper methods to EventConfig:
   - Add method get_all_dates() -> list[date]: Returns list of dates from start_date to end_date
   - Test this helper method

7. Verify tests pass and run just check
```

---

## Phase 2: Configuration and Question Loading

### Step 5: TOML Configuration Loading Activity

**Goal**: Implement activity to load and parse TOML configuration files.

```text
Implement the configuration loading activity with TOML parsing and validation.

1. RED: Write configuration activity tests first:
   - Create tests/unit/test_activities.py:
     - Test that load_event_config() successfully parses valid TOML file
     - Test that load_event_config() returns EventConfig instance with correct values
     - Test that load_event_config() raises FileNotFoundError for missing file
     - Test that load_event_config() raises ValueError for malformed TOML
     - Test that load_event_config() raises ValueError for missing required fields
     - Test that load_event_config() validates date ranges (end > start)

2. Create test fixture TOML file:
   - Create tests/fixtures/config.toml with minimal valid configuration:
     - All required fields from spec section 4.1
     - 3-day event (2025-03-10 to 2025-03-12)
     - 5 questions per day

3. GREEN: Implement configuration loading activity minimally:
   - Create src/activities/config.py:
     - Add file header: "# ABOUTME: Configuration loading activities for event setup.\n# Loads and validates TOML configuration files for trivia events."
     - Import tomli for TOML parsing (or tomllib for Python 3.11+)
     - Import Path from pathlib
     - Import date, time from datetime
     - Import EventConfig from src.models
     - Define load_event_config(config_path: str) -> EventConfig:
       - Read TOML file with tomli.load()
       - Extract all sections: [event], [dates], [questions], [ui.messages], [ui.colors], [features], [s3]
       - Parse date strings to date objects
       - Parse time strings to time objects
       - Create and return EventConfig instance
       - Let pydantic validation handle field validation
       - Add comprehensive docstring with Args, Returns, Raises
     - Add error handling:
       - Catch FileNotFoundError and re-raise with helpful message
       - Catch tomli.TOMLDecodeError and raise ValueError with helpful message

4. REFACTOR: Improve error messages:
   - Add specific error messages for missing sections
   - Add line number information from TOML errors if available

5. Verify tests pass and run just check
```

---

### Step 6: Questions JSON Loading Activity

**Goal**: Implement activity to load and validate questions from JSON files.

```text
Implement the questions loading activity with JSON parsing and schema validation.

1. RED: Write questions activity tests first:
   - Add to tests/unit/test_activities.py:
     - Test that load_questions() successfully parses valid JSON file
     - Test that load_questions() returns dict[str, list[Question]]
     - Test that load_questions() validates each question has exactly 4 options (A, B, C, D)
     - Test that load_questions() validates correct_answer is one of A/B/C/D
     - Test that load_questions() raises FileNotFoundError for missing file
     - Test that load_questions() raises ValueError for malformed JSON
     - Test that load_questions() raises ValueError for questions missing required fields
     - Test that get_questions_for_day() returns correct subset for a date
     - Test that get_questions_for_day() raises KeyError for invalid date

2. Create test fixture questions file:
   - Create tests/fixtures/questions.json with minimal valid data:
     - 3 dates: 2025-03-10, 2025-03-11, 2025-03-12
     - 5 questions per date
     - Each question with valid structure (id, text, options A/B/C/D, correct_answer)

3. GREEN: Implement questions loading activity minimally:
   - Create src/activities/questions.py:
     - Add file header: "# ABOUTME: Question loading activities for retrieving trivia questions.\n# Loads and validates JSON question files with A/B/C/D answer format."
     - Import json, Path
     - Import Question from src.models
     - Define load_questions(file_path: str) -> dict[str, list[Question]]:
       - Read JSON file
       - Parse JSON
       - Iterate through date keys
       - For each date, create list of Question objects from question dicts
       - Let Question's pydantic validation handle schema validation
       - Return dict[str, list[Question]]
       - Add comprehensive docstring
     - Define get_questions_for_day(file_path: str, date: str) -> list[Question]:
       - Call load_questions()
       - Return list for specific date
       - Raise KeyError if date not found
       - Add comprehensive docstring
     - Add error handling:
       - Catch FileNotFoundError and re-raise
       - Catch json.JSONDecodeError and raise ValueError

4. RED: Write questions validation activity tests:
   - Add to tests/unit/test_activities.py:
     - Test that validate_questions_file() succeeds for valid file
     - Test that validate_questions_file() raises ValueError if dates don't match config date range
     - Test that validate_questions_file() raises ValueError if question count per day doesn't match config
     - Test that validate_questions_file() raises ValueError for missing file

5. GREEN: Implement validation activity minimally:
   - Add to src/activities/questions.py:
     - Define validate_questions_file(file_path: str, config: EventConfig) -> None:
       - Call load_questions() to load all questions
       - Get expected dates from config.get_all_dates()
       - Verify all expected dates exist in questions dict
       - Verify each date has exactly config.questions_per_day questions
       - Raise ValueError with specific message if validation fails
       - Add comprehensive docstring

6. Update src/activities/__init__.py:
   - Export load_questions, get_questions_for_day, validate_questions_file

7. REFACTOR: Add caching if needed:
   - Consider caching loaded questions to avoid repeated file reads

8. Verify tests pass and run just check
```

---

### Step 7: Email Validation Activity

**Goal**: Implement email validation activity with consumer domain blocking.

```text
Implement email validation activity with RFC 5322 format checking and work email filtering.

1. RED: Write email validation tests first:
   - Add to tests/unit/test_activities.py:
     - Test that validate_email() returns True for valid work email (user@company.com)
     - Test that validate_email() returns True for any email when require_work_email=False
     - Test that validate_email() returns False for invalid email format (no @)
     - Test that validate_email() returns False for gmail.com when require_work_email=True
     - Test that validate_email() returns False for yahoo.com when require_work_email=True
     - Test that validate_email() returns False for hotmail.com when require_work_email=True
     - Test that validate_email() returns False for outlook.com when require_work_email=True
     - Test that validate_email() returns False for aol.com when require_work_email=True
     - Test that validate_email() returns False for icloud.com when require_work_email=True
     - Test that validate_email() handles empty string gracefully (returns False)

2. GREEN: Implement email validation activity minimally:
   - Create src/activities/email.py:
     - Add file header: "# ABOUTME: Email validation activities for player registration.\n# Validates email format and optionally blocks consumer email domains."
     - Import re for regex
     - Define CONSUMER_DOMAINS as set of blocked domains:
       - {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com"}
     - Define validate_email(email: str, require_work_email: bool) -> bool:
       - Use regex to validate email format (simple RFC 5322 check)
       - Extract domain from email (part after @)
       - If require_work_email is True, check domain not in CONSUMER_DOMAINS
       - Return True if valid, False otherwise
       - Handle exceptions gracefully and return False
       - Add comprehensive docstring

3. Update src/activities/__init__.py:
   - Export validate_email

4. REFACTOR: Improve domain validation:
   - Make CONSUMER_DOMAINS configurable via parameter if needed
   - Add case-insensitive domain checking

5. Verify tests pass and run just check
```

---

### Step 8: S3 CSV Export Activity

**Goal**: Implement CSV export activity with S3 upload functionality.

```text
Implement CSV export activity for generating and uploading player data to S3.

1. RED: Write CSV export tests first:
   - Add to tests/unit/test_activities.py:
     - Test that export_daily_csv_to_s3() creates CSV with correct format
     - Test that CSV includes all players
     - Test that CSV columns match spec: email, first_name, last_name, total_score, dayN_score columns, completed_days
     - Test that CSV day columns are dynamic based on event dates
     - Test that export_daily_csv_to_s3() uploads to S3 with correct key format "marathon-trivia-{date}.csv"
     - Test that export_daily_csv_to_s3() returns S3 URL
     - Test that export_daily_csv_to_s3() handles empty player list gracefully

2. Create test fixtures:
   - Add to tests/fixtures/players.py:
     - Create fixture function create_test_player() that returns Player instance
     - Create fixture function create_test_players() that returns list of 3 test players with different scores

3. GREEN: Implement CSV export activity minimally:
   - Create src/activities/export.py:
     - Add file header: "# ABOUTME: CSV export activities for player data reporting.\n# Generates CSV files and uploads them to S3 for event organizers."
     - Import csv, io, boto3
     - Import Player from src.models
     - Import date from datetime
     - Define export_daily_csv_to_s3(
         bucket: str,
         region: str,
         date: str,
         players: list[Player],
         event_dates: list[str]
       ) -> str:
       - Create in-memory CSV using io.StringIO
       - Build header row: ["email", "first_name", "last_name", "total_score", *day_columns, "completed_days"]
       - Day columns: ["day1_score", "day2_score", ...] based on event_dates
       - Write header row
       - For each player:
         - Write row with email, first_name, last_name, total_score
         - For each event date, write player.daily_scores.get(date, 0)
         - Write len(player.completed_days)
       - Get CSV string from StringIO
       - Upload to S3 using boto3 client
       - Key format: f"marathon-trivia-{date}.csv"
       - Return S3 URL: f"https://{bucket}.s3.{region}.amazonaws.com/marathon-trivia-{date}.csv"
       - Add comprehensive docstring

4. Update src/activities/__init__.py:
   - Export export_daily_csv_to_s3

5. RED: Write integration test with moto:
   - Create tests/integration/test_export.py:
     - Use @mock_aws decorator from moto
     - Test end-to-end CSV generation and S3 upload
     - Verify S3 object exists and has correct content

6. GREEN: Make integration test pass:
   - Ensure export activity works with mocked S3

7. REFACTOR: Add error handling:
   - Add retry logic for S3 upload (3 retries with exponential backoff)
   - Add proper error logging

8. Verify tests pass and run just check
```

---

## Phase 3: Workflow Implementation - Player Entity

### Step 9: PlayerEntityWorkflow - Basic Structure

**Goal**: Implement the basic PlayerEntityWorkflow structure with state management.

```text
Implement the PlayerEntityWorkflow skeleton with basic state initialization and queries.

1. RED: Write PlayerEntityWorkflow initialization tests first:
   - Create tests/unit/test_workflows.py:
     - Import necessary Temporal testing utilities
     - Test that PlayerEntityWorkflow can be started with player info
     - Test that workflow initializes with correct player state (zero scores, empty completed days)
     - Test that workflow query get_current_state() returns PlayerState
     - Test that workflow query get_score_for_day("2025-03-10") returns 0 initially
     - Test that workflow query has_completed_day("2025-03-10") returns False initially

2. Create test fixtures for workflows:
   - Add to tests/fixtures/players.py:
     - Create fixture create_temporal_test_env() that sets up Temporal test environment
     - Follow patterns from temporal-trivia-python

3. GREEN: Implement PlayerEntityWorkflow basic structure:
   - Create src/workflows/player.py:
     - Add file header: "# ABOUTME: PlayerEntityWorkflow maintains per-player state across entire event.\n# Handles answer submission, score tracking, and progress queries for individual players."
     - Import workflow, dataclass
     - Import Player, Question from src.models
     - Define PlayerState dataclass:
       - player: Player
       - current_day: str | None
       - current_question_index: int
     - Define PlayerEntityWorkflow class with @workflow.defn decorator:
       - Add @workflow.run method run(self, player_id: str, email: str, first_name: str, last_name: str) -> None:
         - Initialize self.state with PlayerState containing new Player
         - Use workflow.wait_condition(lambda: False) to keep workflow running indefinitely
       - Add @workflow.query method get_current_state(self) -> PlayerState:
         - Return copy of self.state (defensive copy)
       - Add @workflow.query method get_score_for_day(self, date: str) -> int:
         - Return self.state.player.daily_scores.get(date, 0)
       - Add @workflow.query method has_completed_day(self, date: str) -> bool:
         - Return date in self.state.player.completed_days
       - Add comprehensive docstrings

4. Update src/workflows/__init__.py:
   - Export PlayerEntityWorkflow, PlayerState

5. REFACTOR: Add proper type hints:
   - Ensure all methods have complete type hints
   - Run mypy to verify

6. Verify tests pass and run just check
```

---

### Step 10: PlayerEntityWorkflow - Start Day Update Handler

**Goal**: Implement the start_day update handler to begin a new day of questions.

```text
Implement start_day update handler that loads questions and returns the first question.

1. RED: Write start_day tests first:
   - Add to tests/unit/test_workflows.py:
     - Test that start_day("2025-03-10") returns first Question
     - Test that start_day() sets current_day in state
     - Test that start_day() sets current_question_index to 0
     - Test that start_day() raises error if day already completed
     - Test that start_day() calls get_questions_for_day activity
     - Test that start_day() returns Question with correct structure

2. GREEN: Implement start_day update handler minimally:
   - Update src/workflows/player.py:
     - Add @workflow.update method start_day(self, date: str) -> Question:
       - Check if date already in self.state.player.completed_days
       - If yes, raise ValueError("Day already completed")
       - Call activity get_questions_for_day(file_path, date) to get questions
       - Store questions in workflow state (add questions: dict[str, list[Question]] to PlayerState)
       - Set self.state.current_day = date
       - Set self.state.current_question_index = 0
       - Return questions[0]
       - Add comprehensive docstring
     - Configure activity execution:
       - Use workflow.execute_activity with proper timeouts
       - Set start_to_close_timeout = 10 seconds

3. Update tests to mock activity:
   - Use Temporal's activity mocking to provide test questions
   - Follow patterns from temporal-trivia-python for activity mocking

4. REFACTOR: Add validation:
   - Validate date format (ISO format)
   - Add better error messages

5. Verify tests pass and run just check
```

---

### Step 11: PlayerEntityWorkflow - Submit Answer Update Handler

**Goal**: Implement the submit_answer update handler with answer validation and scoring.

```text
Implement submit_answer update handler that validates answers, updates scores, and returns next question or completion.

1. RED: Write submit_answer tests first:
   - Add to tests/unit/test_workflows.py:
     - Test that submit_answer() with correct answer increments score
     - Test that submit_answer() with incorrect answer does not increment score
     - Test that submit_answer() returns next question if more questions remain
     - Test that submit_answer() returns completion message if all questions answered
     - Test that submit_answer() validates answer_choice is one of ["A", "B", "C", "D"]
     - Test that submit_answer() raises error for invalid answer_choice (e.g., "E")
     - Test that submit_answer() raises error if question_id doesn't match current question
     - Test that submit_answer() raises error if day not started
     - Test that submit_answer() raises error if day already completed
     - Test that submit_answer() marks day as completed after last question
     - Test that submit_answer() updates total_score correctly

2. Define AnswerResult dataclass:
   - Add to src/workflows/player.py:
     - Define AnswerResult dataclass:
       - is_correct: bool
       - correct_answer: str | None  # Only if config.show_correct_answer
       - next_question: Question | None
       - completion_message: str | None
       - current_score: int
       - total_questions: int

3. GREEN: Implement submit_answer update handler minimally:
   - Update src/workflows/player.py:
     - Add @workflow.update method submit_answer(
         self,
         date: str,
         question_id: str,
         answer_choice: str,
         show_correct_answer: bool
       ) -> AnswerResult:
       - Validate date matches current_day, raise ValueError if not
       - Validate answer_choice in ["A", "B", "C", "D"], raise ValueError if not
       - Get current question from state
       - Validate question_id matches current question.id, raise ValueError if not
       - Check if answer is correct: answer_choice == current_question.correct_answer
       - If correct, increment daily score for date
       - Increment total_score
       - Increment current_question_index
       - If more questions remain:
         - Return AnswerResult with next question, no completion message
       - If all questions answered:
         - Mark day as completed
         - Return AnswerResult with completion message, no next question
       - Add comprehensive docstring

4. REFACTOR: Add helper methods:
   - Add _get_current_question() -> Question helper method
   - Add _is_answer_correct(question: Question, answer: str) -> bool helper method

5. Verify tests pass and run just check
```

---

### Step 12: DailyWorkflow - Basic Structure

**Goal**: Implement the DailyWorkflow structure with leaderboard state management.

```text
Implement DailyWorkflow skeleton with daily leaderboard state and queries.

1. RED: Write DailyWorkflow initialization tests first:
   - Add to tests/unit/test_workflows.py:
     - Test that DailyWorkflow can be started with date and questions
     - Test that workflow initializes with empty player_scores and completed_players
     - Test that workflow query get_daily_leaderboard() returns empty list initially
     - Test that workflow query is_day_active() respects day_start_time and day_end_time

2. GREEN: Implement DailyWorkflow basic structure:
   - Create src/workflows/daily.py:
     - Add file header: "# ABOUTME: DailyWorkflow manages a single day's trivia session.\n# Maintains daily leaderboard and receives score updates from players."
     - Import workflow, dataclass
     - Import Question, LeaderboardEntry, EventConfig from src.models
     - Import datetime, time
     - Define DailyState dataclass:
       - date: str
       - questions: list[Question]
       - player_scores: dict[str, int]  # player_id -> score
       - completed_players: set[str]
       - config: EventConfig
     - Define DailyWorkflow class with @workflow.defn decorator:
       - Add @workflow.run method run(self, date: str, questions: list[Question], config: EventConfig) -> None:
         - Initialize self.state with DailyState
         - Use workflow.wait_condition(lambda: False) to keep running
       - Add @workflow.query method get_daily_leaderboard(self) -> list[LeaderboardEntry]:
         - Return empty list for now (will implement ranking in next step)
       - Add @workflow.query method is_day_active(self) -> bool:
         - Get current workflow time
         - Check if current time is between day_start_time and day_end_time
         - Return True/False
       - Add comprehensive docstrings

3. Update src/workflows/__init__.py:
   - Export DailyWorkflow, DailyState

4. REFACTOR: Add time zone support:
   - Use workflow.now() for current time
   - Handle timezone from config

5. Verify tests pass and run just check
```

---

### Step 13: DailyWorkflow - Leaderboard Ranking Logic

**Goal**: Implement leaderboard ranking with tie handling and alphabetical sorting.

```text
Implement leaderboard ranking logic with proper tie handling and alphabetical tie-breaking.

1. RED: Write leaderboard ranking tests first:
   - Add to tests/unit/test_workflows.py:
     - Test that get_daily_leaderboard() returns entries sorted by score descending
     - Test that players with tied scores share the same rank
     - Test that next rank after tie adjusts correctly (5 players at rank 1, next is rank 6)
     - Test that ties are broken alphabetically by last name, then first name
     - Test that leaderboard includes display names in "FirstName L." format
     - Test that empty leaderboard returns empty list

2. Create helper function for ranking:
   - Add to src/workflows/daily.py (outside class):
     - Define calculate_leaderboard(
         player_scores: dict[str, int],
         player_info: dict[str, tuple[str, str, str]]  # player_id -> (email, first, last)
       ) -> list[LeaderboardEntry]:
       - Sort players by score descending, then alphabetically by last name, then first name
       - Assign ranks with tie handling:
         - Track current_rank and rank_offset
         - Players with same score get same rank
         - Next different score gets rank = current_rank + number_of_tied_players
       - Create LeaderboardEntry for each player
       - Return sorted list

3. GREEN: Implement leaderboard query:
   - Update src/workflows/daily.py:
     - Add player_info: dict[str, tuple[str, str, str]] to DailyState
     - Update submit_score update handler to store player info when first score submitted
     - Update get_daily_leaderboard() query:
       - Call calculate_leaderboard(self.state.player_scores, self.state.player_info)
       - Return result
     - Add @workflow.update method submit_score(self, player_id: str, score: int, email: str, first_name: str, last_name: str) -> None:
       - Validate player_id not in completed_players (reject duplicates)
       - Store player info if not already stored
       - Store score in player_scores
       - Add player_id to completed_players
       - Add comprehensive docstring

4. RED: Write submit_score tests:
   - Add to tests/unit/test_workflows.py:
     - Test that submit_score() updates player_scores correctly
     - Test that submit_score() marks player as completed
     - Test that submit_score() rejects duplicate submissions
     - Test that submit_score() validates day is active (if needed)

5. GREEN: Make submit_score tests pass

6. REFACTOR: Extract ranking logic:
   - Move calculate_leaderboard to separate utility module if it grows complex
   - Add comprehensive tests for edge cases (all tied, no players, etc.)

7. Verify tests pass and run just check
```

---

### Step 14: EventWorkflow - Basic Structure

**Goal**: Implement EventWorkflow skeleton with configuration loading and child workflow management.

```text
Implement EventWorkflow skeleton that loads configuration and manages daily child workflows.

1. RED: Write EventWorkflow initialization tests first:
   - Create tests/unit/test_event_workflow.py:
     - Test that EventWorkflow can be started with event_id and config_path
     - Test that workflow loads configuration via load_event_config activity
     - Test that workflow validates questions file via validate_questions_file activity
     - Test that workflow query get_event_status() returns correct status
     - Test that workflow tracks player_count

2. GREEN: Implement EventWorkflow basic structure:
   - Create src/workflows/event.py:
     - Add file header: "# ABOUTME: EventWorkflow manages entire event lifecycle.\n# Coordinates daily child workflows and handles player registration."
     - Import workflow, dataclass
     - Import EventConfig from src.models
     - Define EventState dataclass:
       - event_id: str
       - config: EventConfig
       - daily_workflow_ids: dict[str, str]  # date -> workflow_id
       - player_count: int
       - player_registry: dict[str, str]  # email -> player_id (for duplicate detection)
     - Define EventWorkflow class with @workflow.defn decorator:
       - Add @workflow.run method run(self, event_id: str, config_path: str) -> None:
         - Call load_event_config activity to get config
         - Call validate_questions_file activity to validate questions
         - Initialize self.state with EventState
         - Use workflow.wait_condition(lambda: False) to keep running
       - Add @workflow.query method get_event_status(self) -> dict:
         - Return dict with event_id, player_count, active_days, etc.
       - Add comprehensive docstrings

3. Update src/workflows/__init__.py:
   - Export EventWorkflow, EventState

4. REFACTOR: Add error handling:
   - Handle activity failures for config/questions loading
   - Fail fast if configuration is invalid

5. Verify tests pass and run just check
```

---

### Step 15: EventWorkflow - Player Registration

**Goal**: Implement register_player update handler to create PlayerEntityWorkflow instances.

```text
Implement register_player update handler that creates player entity workflows and handles duplicates.

1. RED: Write register_player tests first:
   - Add to tests/unit/test_event_workflow.py:
     - Test that register_player() creates new PlayerEntityWorkflow
     - Test that register_player() returns player_id
     - Test that register_player() increments player_count
     - Test that register_player() stores email -> player_id mapping
     - Test that register_player() returns existing player_id for duplicate email
     - Test that register_player() validates email via validate_email activity

2. GREEN: Implement register_player update handler:
   - Update src/workflows/event.py:
     - Add @workflow.update method register_player(
         self,
         email: str,
         first_name: str,
         last_name: str
       ) -> str:
       - Check if email already in player_registry
       - If yes, return existing player_id (handle duplicate)
       - Call validate_email activity
       - If email invalid, raise ValueError
       - Generate new player_id using workflow.uuid4()
       - Start PlayerEntityWorkflow as child workflow:
         - Use workflow.start_child_workflow
         - Pass player_id, email, first_name, last_name
         - Use player_id as workflow_id for idempotency
       - Store email -> player_id in registry
       - Increment player_count
       - Return player_id
       - Add comprehensive docstring

3. REFACTOR: Add player lookup helper:
   - Add @workflow.query method get_player_id_by_email(self, email: str) -> str | None:
     - Return player_id if email in registry, else None

4. Verify tests pass and run just check
```

---

### Step 16: EventWorkflow - Daily Workflow Scheduling

**Goal**: Implement daily workflow scheduling with timers.

```text
Implement daily child workflow scheduling that starts DailyWorkflow instances at configured times.

1. RED: Write daily workflow scheduling tests first:
   - Add to tests/unit/test_event_workflow.py:
     - Test that EventWorkflow schedules DailyWorkflow for each event day
     - Test that DailyWorkflow starts at day_start_time
     - Test that workflow tracks daily_workflow_ids correctly
     - Test that workflow passes correct questions to each DailyWorkflow

2. GREEN: Implement daily workflow scheduling:
   - Update src/workflows/event.py:
     - Update run() method to schedule daily workflows:
       - Get all event dates from config.get_all_dates()
       - For each date:
         - Calculate start datetime (date + day_start_time in config.timezone)
         - Use workflow.wait(workflow.datetime_to_duration(start_datetime)) to wait until start time
         - Call load_questions activity to get questions for date
         - Start DailyWorkflow as child workflow:
           - Pass date, questions, config
           - Use f"{event_id}-{date}" as workflow_id
         - Store workflow_id in daily_workflow_ids
       - Add comprehensive docstring

3. REFACTOR: Add helper method:
   - Add _schedule_daily_workflow(self, date: date) -> str method
   - Refactor scheduling logic into helper

4. Verify tests pass and run just check
```

---

## Phase 4: API Layer Implementation

### Step 17: FastAPI Application Setup

**Goal**: Set up the FastAPI application with basic structure and health endpoint.

```text
Set up FastAPI application with basic configuration, Temporal client, and health check endpoint.

1. RED: Write API setup tests first:
   - Create tests/unit/test_api.py:
     - Test that FastAPI app can be created
     - Test that GET /health returns {"status": "ok"}
     - Test that app has Temporal client configured

2. GREEN: Implement FastAPI app setup:
   - Create src/api/main.py:
     - Add file header: "# ABOUTME: FastAPI application entry point for Marathon Trivia Platform.\n# Configures routes, Temporal client, Redis connection, and middleware."
     - Import FastAPI, HTTPException
     - Import os for env vars
     - Import temporalio.client.Client
     - Create FastAPI app instance
     - Add lifespan context manager:
       - On startup: Connect to Temporal, connect to Redis
       - On shutdown: Close connections
     - Add GET /health endpoint:
       - Return {"status": "ok"}
     - Add comprehensive docstrings

3. Create Redis cache utility:
   - Create src/api/cache.py:
     - Add file header: "# ABOUTME: Redis caching utilities for API responses.\n# Provides caching for leaderboard, player state, and config data."
     - Import redis
     - Define RedisCache class:
       - __init__(self, redis_url: str)
       - async get(key: str) -> str | None
       - async set(key: str, value: str, ttl: int | None = None) -> None
       - async delete(key: str) -> None
     - Add comprehensive docstrings

4. Update main.py to create RedisCache instance:
   - Add redis_cache as app.state.redis_cache

5. RED: Write cache tests:
   - Add to tests/unit/test_api.py:
     - Test that RedisCache can get/set values
     - Test that RedisCache respects TTL
     - Use fakeredis for testing

6. GREEN: Make cache tests pass

7. REFACTOR: Add configuration management:
   - Load environment variables properly
   - Add validation for required env vars

8. Verify tests pass and run just check
```

---

### Step 18: API Routes - Player Registration

**Goal**: Implement POST /api/join endpoint for player registration.

```text
Implement player registration endpoint that creates players via EventWorkflow.

1. RED: Write player registration endpoint tests first:
   - Add to tests/unit/test_api.py:
     - Test that POST /api/join with valid data returns HTML fragment
     - Test that POST /api/join sets player_id cookie
     - Test that POST /api/join validates email format
     - Test that POST /api/join validates work email if configured
     - Test that POST /api/join handles duplicate email (returns existing player)
     - Test that POST /api/join returns error HTML for invalid email

2. GREEN: Implement player registration endpoint:
   - Create src/api/routes/player.py:
     - Add file header: "# ABOUTME: Player management API routes.\n# Handles player registration and state queries."
     - Import APIRouter, Form, Response, Cookie
     - Import Jinja2Templates for rendering
     - Create router = APIRouter()
     - Add POST /api/join endpoint:
       - Parameters: first_name: str = Form(), last_name: str = Form(), email: str = Form()
       - Get Temporal client from app.state
       - Get EventWorkflow handle
       - Call register_player update handler with email, first_name, last_name
       - Get player_id from response
       - Set player_id cookie
       - Return HTML fragment with success message and redirect
       - Handle errors and return error HTML fragment
     - Add comprehensive docstrings

3. Create HTML templates:
   - Create frontend/templates/components/join-success.html:
     - Success message
     - Redirect to main page
   - Create frontend/templates/components/error.html:
     - Error message with "Back to Home" button

4. Update src/api/main.py:
   - Import and include player router
   - Configure Jinja2Templates

5. REFACTOR: Add template rendering utility:
   - Create src/api/templates.py:
     - Add file header: "# ABOUTME: Template rendering utilities.\n# Provides Jinja2 template rendering for HTML fragments."
     - Define render_template() helper function

6. Verify tests pass and run just check
```

---

### Step 19: API Routes - Gameplay Start Day

**Goal**: Implement GET /api/day/{date}/start endpoint to begin a day's questions.

```text
Implement start day endpoint that calls PlayerEntityWorkflow.start_day and returns first question.

1. RED: Write start day endpoint tests first:
   - Add to tests/unit/test_api.py:
     - Test that GET /api/day/{date}/start returns HTML fragment with first question
     - Test that endpoint requires player_id cookie
     - Test that endpoint validates day has started
     - Test that endpoint validates day hasn't ended
     - Test that endpoint validates player hasn't completed day
     - Test that endpoint returns error HTML for invalid date
     - Test that endpoint returns error HTML if day already completed

2. GREEN: Implement start day endpoint:
   - Create src/api/routes/gameplay.py:
     - Add file header: "# ABOUTME: Gameplay API routes for answering questions.\n# Handles starting days, submitting answers, and returning questions."
     - Import APIRouter, Cookie, Path
     - Create router = APIRouter()
     - Add GET /api/day/{date}/start endpoint:
       - Parameters: date: str = Path(), player_id: str = Cookie()
       - Get Temporal client from app.state
       - Get PlayerEntityWorkflow handle using player_id
       - Call start_day(date) update handler
       - Get first Question from response
       - Render question.html template with question data
       - Return HTML fragment
       - Handle errors and return error HTML
     - Add comprehensive docstrings

3. Create question template:
   - Create frontend/templates/components/question.html:
     - Display question number and total
     - Display question text
     - Display 4 radio button options (A/B/C/D)
     - Form with hx-post="/api/day/{date}/answer"
     - Submit button

4. Update src/api/main.py:
   - Import and include gameplay router

5. REFACTOR: Add validation helper:
   - Add validate_player_cookie() helper function
   - Add get_workflow_handle() helper function

6. Verify tests pass and run just check
```

---

### Step 20: API Routes - Submit Answer

**Goal**: Implement POST /api/day/{date}/answer endpoint to submit answers and get next question.

```text
Implement answer submission endpoint that validates answers and returns next question or completion.

1. RED: Write submit answer endpoint tests first:
   - Add to tests/unit/test_api.py:
     - Test that POST /api/day/{date}/answer with correct answer returns correct feedback
     - Test that POST /api/day/{date}/answer with incorrect answer returns incorrect feedback
     - Test that endpoint returns next question if more remain
     - Test that endpoint returns completion message if all questions answered
     - Test that endpoint validates answer_choice is one of A/B/C/D
     - Test that endpoint requires player_id cookie
     - Test that endpoint returns error HTML for invalid answer_choice

2. GREEN: Implement submit answer endpoint:
   - Update src/api/routes/gameplay.py:
     - Add POST /api/day/{date}/answer endpoint:
       - Parameters:
         - date: str = Path()
         - question_id: str = Form()
         - answer_choice: str = Form()
         - player_id: str = Cookie()
       - Get Temporal client and EventConfig from app.state
       - Get PlayerEntityWorkflow handle
       - Call submit_answer(date, question_id, answer_choice, config.show_correct_answer) update handler
       - Get AnswerResult from response
       - If next_question exists:
         - Render question.html with next question
       - Else:
         - Render completion.html with completion message and score
       - Return HTML fragment
       - Handle errors and return error HTML
     - Add comprehensive docstrings

3. Create completion template:
   - Create frontend/templates/components/completion.html:
     - "Day Complete!" heading
     - Display score: "Your score: {score}/{total}"
     - Display completion message from config
     - Link back to leaderboard

4. Update answer feedback template:
   - Create frontend/templates/components/answer-feedback.html:
     - Show "✓ Correct!" or "✗ Incorrect. The answer was: {correct_option}"
     - Only show correct answer if config.show_correct_answer is True

5. REFACTOR: Add score submission to DailyWorkflow:
   - After submit_answer succeeds, call DailyWorkflow.submit_score with player's final score
   - Handle errors gracefully

6. Verify tests pass and run just check
```

---

### Step 21: API Routes - Leaderboard

**Goal**: Implement GET /api/leaderboard endpoint with Redis caching.

```text
Implement leaderboard endpoint that aggregates daily leaderboards and caches results.

1. RED: Write leaderboard endpoint tests first:
   - Add to tests/unit/test_api.py:
     - Test that GET /api/leaderboard returns HTML table fragment
     - Test that leaderboard is cached in Redis for 30 seconds
     - Test that leaderboard aggregates scores from all DailyWorkflows
     - Test that leaderboard shows correct ranking with ties
     - Test that leaderboard shows daily scores per player
     - Test that leaderboard uses fakeredis for testing

2. GREEN: Implement leaderboard endpoint:
   - Create src/api/routes/leaderboard.py:
     - Add file header: "# ABOUTME: Leaderboard API routes.\n# Provides leaderboard display and player search functionality."
     - Import APIRouter
     - Create router = APIRouter()
     - Add GET /api/leaderboard endpoint:
       - Check Redis cache for key "leaderboard:full"
       - If cached, return cached HTML
       - Else:
         - Get Temporal client from app.state
         - Get EventWorkflow handle
         - Get list of daily_workflow_ids from query
         - For each DailyWorkflow:
           - Query get_daily_leaderboard()
           - Aggregate results
         - Sort by total_score descending, then alphabetically
         - Calculate ranks with tie handling
         - Render leaderboard.html template
         - Cache result in Redis with 30 second TTL
         - Return HTML fragment
     - Add comprehensive docstrings

3. Create leaderboard template:
   - Create frontend/templates/components/leaderboard.html:
     - HTML table with headers: Rank, Player, Total, Day 1, Day 2, Day 3, etc.
     - Dynamic day columns based on event dates
     - Rows for each LeaderboardEntry
     - Apply rank-N class for styling

4. Update src/api/main.py:
   - Import and include leaderboard router

5. REFACTOR: Extract aggregation logic:
   - Create helper function aggregate_leaderboards(daily_leaderboards: list[list[LeaderboardEntry]]) -> list[LeaderboardEntry]
   - Test helper function separately

6. Verify tests pass and run just check
```

---

### Step 22: API Routes - Configuration and Player Lookup

**Goal**: Implement GET /api/config and GET /api/player endpoints.

```text
Implement configuration and player lookup endpoints.

1. RED: Write config and player endpoints tests first:
   - Add to tests/unit/test_api.py:
     - Test that GET /api/config returns JSON with event config
     - Test that GET /api/config is cached permanently
     - Test that GET /api/player returns HTML with player's rank highlighted
     - Test that GET /api/player requires player_id cookie

2. GREEN: Implement config endpoint:
   - Update src/api/routes/leaderboard.py:
     - Add GET /api/config endpoint:
       - Check Redis cache for key "config:event"
       - If cached, return cached JSON
       - Else:
         - Get EventConfig from app.state (loaded at startup)
         - Build JSON response with title, description, dates, colors
         - Cache result in Redis with no expiration
         - Return JSON

3. GREEN: Implement player lookup endpoint:
   - Update src/api/routes/player.py:
     - Add GET /api/player endpoint:
       - Parameters: player_id: str = Cookie()
       - Get PlayerEntityWorkflow handle
       - Query get_current_state()
       - Get player email from state
       - Fetch full leaderboard (call /api/leaderboard logic)
       - Find player's entry in leaderboard
       - Render leaderboard.html with player's row highlighted
       - Return HTML fragment

4. Update templates:
   - Update leaderboard.html to support highlighting a specific player

5. REFACTOR: Cache player state:
   - Add caching for player state queries with 10 second TTL

6. Verify tests pass and run just check
```

---

## Phase 5: Frontend and Integration

### Step 23: Frontend Templates - Landing Page

**Goal**: Implement the landing page with join form and returning player view.

```text
Implement landing page templates for first-time and returning players.

1. Create base template:
   - Create frontend/templates/base.html:
     - HTML5 doctype
     - Include Tailwind CSS via CDN
     - Include HTMX via script tag
     - Define CSS variables for colors from config
     - Meta tags for responsive design
     - Block for content

2. Create landing page template:
   - Create frontend/templates/landing.html:
     - Extend base.html
     - Display event title and description from config
     - If no player_id cookie (first-time visitor):
       - Show join form with first_name, last_name, email inputs
       - Form uses hx-post="/api/join" hx-target="#main"
     - If player_id cookie exists (returning player):
       - Show day buttons for each event day
       - Button states: disabled for past/future days, enabled for current day
       - Each button uses hx-get="/api/day/{date}/start"
       - Show leaderboard container with hx-get="/api/leaderboard" hx-trigger="load, every 30s"
       - Show "Find My Rank" button with hx-get="/api/player"

3. Create day button component:
   - Create frontend/templates/components/day-button.html:
     - Button with day label ("Day 1", "Day 2", etc.)
     - Dynamic state: active, completed, inactive
     - HTMX attributes for loading questions

4. Add landing page route:
   - Update src/api/main.py:
     - Add GET / endpoint:
       - Check for player_id cookie
       - Get event config
       - Render landing.html with appropriate data
       - Return HTML

5. Test landing page rendering:
   - Add to tests/unit/test_api.py:
     - Test GET / without cookie shows join form
     - Test GET / with cookie shows day buttons and leaderboard

6. Verify templates render correctly with just check
```

---

### Step 24: Frontend Styling with Tailwind

**Goal**: Apply Tailwind CSS styling for responsive, clean UI suitable for trade shows.

```text
Style the frontend with Tailwind CSS for clean, high-contrast, trade-show-friendly design.

1. Update base template with Tailwind configuration:
   - Update frontend/templates/base.html:
     - Add Tailwind config for custom colors from event.toml
     - Define CSS custom properties for primary, secondary, background, text colors
     - Set up responsive breakpoints
     - Configure high-contrast mode for accessibility

2. Style landing page:
   - Update frontend/templates/landing.html:
     - Center container with max-width
     - Large, bold title with primary color
     - Clean form styling with proper spacing
     - Button styling with hover states
     - Responsive grid for day buttons
     - Clean table styling for leaderboard

3. Style question components:
   - Update frontend/templates/components/question.html:
     - Card-based layout with shadow
     - Large, readable text for question
     - Radio buttons with custom styling
     - Clear visual hierarchy
     - Mobile-responsive radio button layout

4. Style leaderboard:
   - Update frontend/templates/components/leaderboard.html:
     - Striped table rows for readability
     - Highlight top 3 ranks with different colors
     - Sticky header for scrolling
     - Responsive column hiding on mobile
     - High contrast for booth displays

5. Style completion and error components:
   - Update frontend/templates/components/completion.html:
     - Success message styling
     - Score display with large numbers
     - Clear call-to-action button
   - Update frontend/templates/components/error.html:
     - Error message styling with icon
     - Clear error text
     - Prominent "Back" button

6. Create custom CSS if needed:
   - Create frontend/static/css/styles.css:
     - Any custom styles not covered by Tailwind
     - Smooth transitions
     - Focus states for accessibility

7. Test styling:
   - Manual testing: View pages in browser
   - Check responsive design at different breakpoints
   - Verify high contrast for readability

8. Verify styling looks good
```

---

### Step 25: Worker and Temporal Client Setup

**Goal**: Implement the Temporal worker that registers workflows and activities.

```text
Implement the Temporal worker entry point that registers all workflows and activities.

1. GREEN: Implement worker:
   - Create src/worker.py:
     - Add file header: "# ABOUTME: Temporal worker entry point.\n# Registers workflows and activities, connects to Temporal server."
     - Import asyncio, os
     - Import temporalio.client.Client, temporalio.worker.Worker
     - Import all workflows: EventWorkflow, DailyWorkflow, PlayerEntityWorkflow
     - Import all activities from src.activities
     - Define async main() function:
       - Load env vars for Temporal connection
       - Create Temporal client:
         - If TLS cert/key provided, use TLS connection
         - Else, use plaintext connection
       - Create Worker:
         - Register all workflows
         - Register all activities
         - Set task queue from env var
       - Run worker
     - Add if __name__ == "__main__": asyncio.run(main())
     - Add comprehensive docstring

2. Create connection utility:
   - Create src/temporal_client.py:
     - Add file header: "# ABOUTME: Temporal client connection utilities.\n# Provides helper functions for creating Temporal clients with TLS support."
     - Define async create_temporal_client() -> Client:
       - Read env vars: TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, TEMPORAL_TLS_CERT_PATH, TEMPORAL_TLS_KEY_PATH
       - If TLS paths provided:
         - Load cert and key from files
         - Create client with TLS config
       - Else:
         - Create plaintext client
       - Return client
     - Add comprehensive docstring

3. RED: Write worker tests:
   - Create tests/unit/test_worker.py:
     - Test that worker can be created with workflows and activities
     - Test that create_temporal_client() handles TLS configuration
     - Test that create_temporal_client() handles plaintext connection

4. GREEN: Make worker tests pass

5. Update API to use connection utility:
   - Update src/api/main.py:
     - Use create_temporal_client() in lifespan

6. Verify worker can start successfully:
   - Run: uv run python src/worker.py
   - Check logs for successful registration

7. Verify tests pass and run just check
```

---

### Step 26: Integration Test - Full Player Journey

**Goal**: Write end-to-end integration test for complete player journey.

```text
Write integration test that simulates complete player journey from registration to leaderboard.

1. RED: Write full player journey integration test:
   - Create tests/integration/test_player_journey.py:
     - Test player_can_join_answer_questions_and_see_leaderboard:
       - Set up Temporal test environment
       - Start EventWorkflow with test config
       - Call register_player to create player
       - Call PlayerEntityWorkflow.start_day for day 1
       - Submit answers to all questions for day 1
       - Verify player's score is updated
       - Query DailyWorkflow leaderboard
       - Verify player appears on leaderboard
       - Verify player's day is marked completed
     - Test player_can_play_multiple_days:
       - Register player
       - Complete day 1 questions
       - Complete day 2 questions
       - Verify total_score accumulates correctly
       - Verify daily_scores has entries for both days
     - Test duplicate_email_returns_existing_player:
       - Register player with email@example.com
       - Register again with same email
       - Verify same player_id returned

2. GREEN: Make integration tests pass:
   - Ensure all workflows and activities work together
   - Fix any integration issues discovered

3. REFACTOR: Extract test helpers:
   - Create tests/fixtures/temporal_test_helpers.py:
     - create_test_event_workflow() helper
     - create_test_player() helper
     - answer_all_questions() helper

4. Verify integration tests pass with just test-integration
```

---

### Step 27: Integration Test - Leaderboard Aggregation

**Goal**: Test leaderboard aggregation across multiple days and players.

```text
Write integration test for leaderboard aggregation with multiple players and days.

1. RED: Write leaderboard aggregation integration test:
   - Create tests/integration/test_leaderboard.py:
     - Test leaderboard_aggregates_scores_correctly:
       - Start EventWorkflow with 3-day config
       - Register 5 players
       - Have all players complete day 1 with different scores
       - Have all players complete day 2 with different scores
       - Query leaderboard
       - Verify total scores are correct
       - Verify ranking is correct
       - Verify daily scores are shown correctly
     - Test leaderboard_handles_ties_correctly:
       - Register 3 players with same total score
       - Query leaderboard
       - Verify all 3 have rank 1
       - Register 1 more player with lower score
       - Verify new player has rank 4 (not rank 2)
     - Test leaderboard_alphabetical_tie_breaking:
       - Register players: "John Doe", "Alice Brown", "Bob Adams" with same scores
       - Query leaderboard
       - Verify order: Adams, Brown, Doe (alphabetical by last name)

2. GREEN: Make leaderboard integration tests pass:
   - Fix any ranking or aggregation bugs

3. REFACTOR: Add edge case tests:
   - Test with 0 players
   - Test with 1000+ players (performance test)

4. Verify integration tests pass with just test-integration
```

---

## Phase 6: Deployment and Documentation

### Step 28: Docker Configuration

**Goal**: Create Docker and Docker Compose configuration for deployment.

```text
Create Docker and Docker Compose configuration for containerized deployment.

1. Create Dockerfile:
   - Create Dockerfile at project root:
     - FROM python:3.11-slim
     - Set WORKDIR /app
     - Install uv: RUN pip install uv
     - Copy pyproject.toml and uv.lock
     - Run uv sync --frozen
     - Copy src/ and frontend/ directories
     - Set CMD ["python", "src/worker.py"]
     - Add proper caching layers

2. Create docker-compose.yml:
   - Create docker-compose.yml at project root:
     - Version: '3.8'
     - Services:
       - temporal: temporalio/auto-setup:latest with SQLite
       - redis: redis:7-alpine
       - worker: build from Dockerfile, depends on temporal and redis
       - api: build from Dockerfile, depends on temporal, redis, worker
     - Volumes:
       - Mount config/ and frontend/ for easy updates
     - Environment variables from .env file
     - Port mappings: 8000 for API, 7233 for Temporal

3. Create .dockerignore:
   - Ignore .venv, __pycache__, .pytest_cache, .mypy_cache
   - Ignore .git, .gitignore
   - Ignore tests/ and docs/ for smaller image

4. Test Docker build:
   - Run: docker build -t marathon-trivia .
   - Verify build succeeds

5. Test Docker Compose:
   - Run: docker-compose up
   - Verify all services start
   - Verify API is accessible at http://localhost:8000
   - Verify Temporal UI at http://localhost:8233

6. Create docker-compose.dev.yml for development:
   - Add volume mounts for hot reloading
   - Enable debug logging

7. Document Docker usage:
   - Add Docker commands to README.md
```

---

### Step 29: Justfile and Development Commands

**Goal**: Create comprehensive Justfile with all development commands.

```text
Create Justfile with all development, testing, and deployment commands.

1. Create Justfile:
   - Create Justfile at project root:
     - Add development commands:
       - dev: Start all services (docker-compose up)
       - worker: Run Temporal worker locally
       - api: Run FastAPI with uvicorn --reload
     - Add testing commands:
       - test: Run all tests with coverage
       - test-unit: Run unit tests only (pytest tests/unit/)
       - test-integration: Run integration tests only (pytest tests/integration/)
       - coverage: Run tests with coverage report (pytest --cov=src --cov-report=html)
     - Add linting commands:
       - lint: Run ruff check src/ tests/
       - format: Run ruff format src/ tests/
       - typecheck: Run mypy --strict src/
       - check: Run lint, typecheck, and test sequentially
     - Add Docker commands:
       - build: docker build -t marathon-trivia .
       - up: docker-compose up
       - down: docker-compose down
       - logs: docker-compose logs -f
     - Add data commands:
       - export-csv: Manually trigger CSV export
       - validate-config: Validate event.toml and questions.json
     - Add comprehensive comments

2. Test all Justfile commands:
   - Run: just check
   - Verify all commands work

3. Document Justfile in README:
   - Add section listing all available commands
```

---

### Step 30: Example Configuration Files

**Goal**: Create example configuration files for easy event setup.

```text
Create example configuration files with comprehensive documentation.

1. Create example TOML config:
   - Create config/event.example.toml:
     - Complete example with all fields from spec
     - Helpful comments explaining each section
     - Example for a 3-day conference event

2. Create example questions JSON:
   - Create config/questions.example.json:
     - 3 days of sample questions (5 questions per day)
     - Mix of easy, medium, hard questions
     - Comments showing question structure

3. Update .env.example:
   - Add comments explaining each variable
   - Add examples for both local and Temporal Cloud

4. Create config validator script:
   - Create scripts/validate_config.py:
     - Load event.toml
     - Load questions.json
     - Validate all fields
     - Check date consistency
     - Check question counts match config
     - Print helpful error messages

5. Test config validator:
   - Run on example files
   - Run on intentionally broken files
   - Verify error messages are helpful

6. Document configuration in docs/how-to/create-event.md
```

---

### Step 31: API Documentation

**Goal**: Create comprehensive API documentation with examples.

```text
Create comprehensive API documentation with endpoint specifications and examples.

1. Create endpoint documentation:
   - Create docs/api/endpoints.md:
     - Document all API endpoints:
       - POST /api/join: Registration with request/response examples
       - GET /api/player: Player lookup with examples
       - GET /api/day/{date}/start: Start day with examples
       - POST /api/day/{date}/answer: Submit answer with examples
       - GET /api/leaderboard: Leaderboard with examples
       - GET /api/config: Configuration with examples
       - GET /health: Health check
     - For each endpoint:
       - Path and method
       - Parameters (path, query, form, cookies)
       - Request format
       - Response format (HTML fragments)
       - Error responses
       - Example curl commands

2. Create workflow documentation:
   - Create docs/api/workflows.md:
     - Document EventWorkflow:
       - Purpose and lifecycle
       - State structure
       - Update handlers with parameters
       - Queries with return types
       - Activities called
     - Document DailyWorkflow:
       - Purpose and lifecycle
       - State structure
       - Update handlers
       - Queries
     - Document PlayerEntityWorkflow:
       - Purpose and lifecycle
       - State structure
       - Update handlers
       - Queries
     - Add state diagrams using Mermaid

3. Create activity documentation:
   - Create docs/api/activities.md:
     - Document each activity:
       - load_event_config: Parameters, returns, failure modes
       - validate_questions_file: Parameters, returns, failure modes
       - load_questions: Parameters, returns
       - get_questions_for_day: Parameters, returns
       - validate_email: Parameters, returns
       - export_daily_csv_to_s3: Parameters, returns, retry policy

4. Create data models documentation:
   - Create docs/api/data-models.md:
     - Document all dataclasses:
       - Question: Fields, validation rules
       - Player: Fields, methods, usage
       - LeaderboardEntry: Fields, usage
       - EventConfig: Fields, validation rules
     - Add examples for each model

5. Enhance FastAPI OpenAPI docs:
   - Update all API endpoints with comprehensive docstrings
   - Add examples to endpoint decorators
   - Add response model schemas
   - Verify /docs and /redoc render properly

6. Test documentation:
   - Verify all examples work
   - Verify curl commands succeed
```

---

### Step 32: How-To Guides

**Goal**: Create practical how-to guides for common tasks.

```text
Create practical how-to guides for setup, deployment, and operations.

1. Create setup guide:
   - Create docs/how-to/setup.md:
     - Prerequisites: Python 3.11+, Redis, Temporal CLI
     - Installing Temporal CLI
     - Installing Redis
     - Setting up virtual environment with uv
     - Running uv sync
     - Setting up .env file
     - Running Temporal dev server
     - Running Redis
     - Starting worker
     - Starting API
     - Accessing the application
     - Troubleshooting common setup issues

2. Create deployment guide:
   - Create docs/how-to/deployment.md:
     - Docker Compose deployment:
       - Prerequisites
       - Building images
       - Starting services
       - Verifying deployment
     - Temporal Cloud deployment:
       - Creating namespace
       - Getting TLS certificates
       - Configuring environment variables
       - Deploying worker and API
     - Production considerations:
       - Scaling workers
       - Redis persistence
       - S3 bucket setup
       - Monitoring

3. Create event creation guide:
   - Create docs/how-to/create-event.md:
     - Copying example config files
     - Customizing event.toml:
       - Setting dates and times
       - Configuring messages
       - Setting colors
       - Feature flags
     - Creating questions.json:
       - Question format
       - Organizing by date
       - Validation
     - Running config validator
     - Starting the event
     - Testing before launch

4. Create monitoring guide:
   - Create docs/how-to/monitoring.md:
     - Accessing Temporal UI
     - Viewing workflow executions
     - Checking workflow history
     - Debugging failed workflows
     - Viewing logs
     - Accessing CSV exports in S3
     - Monitoring player count
     - Checking leaderboard

5. Create troubleshooting guide:
   - Create docs/how-to/troubleshooting.md:
     - Common issues and solutions:
       - "Worker not connecting to Temporal"
       - "Questions file not found"
       - "Invalid email validation"
       - "Player can't submit answer"
       - "Leaderboard not updating"
       - "CSV export failed"
     - Debugging workflows
     - Checking logs
     - Resetting state
     - Manual recovery procedures

6. Test all guides:
   - Follow each guide step-by-step
   - Verify instructions are accurate
   - Update based on testing
```

---

### Step 33: README and Project Documentation

**Goal**: Create comprehensive README with quick start and project overview.

```text
Create project README and update CLAUDE.md with implementation learnings.

1. Create README.md:
   - Project title and description
   - Key features bullet list
   - Architecture diagram
   - Quick start guide:
     - Prerequisites
     - Installation steps
     - Running locally
     - Accessing the application
   - Configuration section:
     - Link to create-event.md
     - Brief config overview
   - Development section:
     - Available Just commands
     - Running tests
     - Linting and type checking
   - Deployment section:
     - Docker Compose
     - Temporal Cloud
   - Documentation links:
     - API docs
     - How-to guides
     - Troubleshooting
   - Contributing guidelines
   - License

2. Update CLAUDE.md:
   - Add implementation learnings:
     - Patterns that worked well
     - Challenges encountered
     - Temporal-specific insights
     - Testing strategies used
   - Add project status:
     - What's implemented
     - Known limitations
     - Future enhancements
   - Add development notes:
     - Key design decisions
     - Architecture trade-offs
     - Performance considerations

3. Create CONTRIBUTING.md:
   - Code style guidelines
   - Testing requirements
   - PR process
   - Commit message format

4. Create LICENSE:
   - Choose appropriate license
   - Add license file

5. Verify documentation:
   - Check all links work
   - Verify formatting renders correctly
   - Test quick start instructions
```

---

### Step 34: End-to-End Testing

**Goal**: Write comprehensive end-to-end tests for complete event lifecycle.

```text
Write end-to-end tests that simulate complete event lifecycle.

1. RED: Write end-to-end event lifecycle test:
   - Create tests/integration/test_event_lifecycle.py:
     - Test complete_event_lifecycle:
       - Start Temporal test environment
       - Create test config for 3-day event
       - Create test questions for 3 days
       - Start EventWorkflow
       - Register 10 players
       - Simulate day 1:
         - Wait until day 1 start time
         - All players start day 1
         - All players answer questions
         - Verify leaderboard updates
       - Simulate day 2:
         - Wait until day 2 start time
         - All players start day 2
         - Some players answer correctly, some incorrectly
         - Verify leaderboard reflects new scores
       - Simulate day 3:
         - Wait until day 3 start time
         - Half of players complete day 3
         - Verify final leaderboard
         - Verify CSV export happens
       - Verify final results:
         - Check all player scores
         - Check leaderboard ranking
         - Check CSV contains all players
     - Test time_based_day_transitions:
       - Verify DailyWorkflow starts at day_start_time
       - Verify DailyWorkflow rejects submissions before start
       - Verify DailyWorkflow rejects submissions after end
       - Verify CSV export triggers at day_end_time

2. GREEN: Make end-to-end tests pass:
   - Fix any issues discovered
   - Ensure all components integrate properly

3. Create performance test:
   - Create tests/integration/test_performance.py:
     - Test with 100 concurrent players
     - Verify leaderboard query time < 2 seconds
     - Verify answer submission time < 500ms

4. Verify all integration tests pass with just test-integration
```

---

### Step 35: Final Testing and Quality Assurance

**Goal**: Verify all tests pass, achieve 80%+ coverage, and ensure code quality.

```text
Run comprehensive testing and quality checks to ensure project meets all requirements.

1. Run full test suite:
   - Run: just test
   - Verify all unit tests pass
   - Verify all integration tests pass
   - Verify no test failures

2. Check test coverage:
   - Run: just coverage
   - Verify coverage >= 80% across all modules
   - Identify any untested code paths
   - Add tests for any gaps

3. Run type checking:
   - Run: just typecheck
   - Verify mypy passes with --strict mode
   - Fix any type errors

4. Run linting:
   - Run: just lint
   - Verify ruff passes with no errors
   - Fix any linting issues

5. Run formatting:
   - Run: just format
   - Verify code is properly formatted

6. Run full check:
   - Run: just check
   - Verify all checks pass (lint, typecheck, test)

7. Manual testing:
   - Start Docker Compose: just up
   - Access application at http://localhost:8000
   - Test player registration
   - Test answering questions
   - Test leaderboard display
   - Test multiple players
   - Test day transitions
   - Verify Temporal UI shows workflows
   - Verify Redis contains cached data

8. Load testing:
   - Test with 100+ concurrent players
   - Verify performance meets requirements
   - Check for any bottlenecks

9. Security review:
   - Verify no secrets in code
   - Check CORS configuration
   - Verify input validation
   - Check for SQL injection risks (none, using workflows)
   - Check for XSS risks in HTML rendering

10. Documentation review:
    - Verify all docs are accurate
    - Check all links work
    - Verify examples work
    - Update any outdated information

11. Final verification:
    - Verify all success criteria from spec are met
    - Check all functional requirements
    - Check all technical requirements
    - Check all documentation requirements
    - Check all performance requirements

12. Create release:
    - Tag version 1.0.0
    - Create GitHub release
    - Document known limitations
    - Document future enhancements
```

---

## Implementation Guidelines

### TDD Process for Each Step

For every implementation step:

1. **RED Phase**: Write failing tests first
   - Define desired behavior through tests
   - Focus on YOUR application logic, not framework behavior
   - Run tests and verify they fail as expected

2. **GREEN Phase**: Write minimal code to pass tests
   - Implement just enough to make tests green
   - Don't add extra features or "nice-to-haves"
   - Keep it simple and focused

3. **REFACTOR Phase**: Improve code while keeping tests green
   - Extract duplicated code
   - Improve naming
   - Add documentation
   - Optimize if needed
   - Run tests after each change

### Testing Focus

**DO test**:
- Question validation logic (A/B/C/D format, correct_answer validation)
- Player display name formatting (FirstName L.)
- Email validation and consumer domain blocking
- Leaderboard ranking with ties and alphabetical sorting
- Score accumulation across multiple days
- Answer validation and scoring logic
- Workflow state management and transitions
- CSV export formatting and S3 upload
- Configuration validation (date ranges, question counts)
- API endpoint business logic (player registration, answer submission)

**DO NOT test**:
- Pydantic validation framework itself
- Temporal SDK functionality
- FastAPI routing mechanism
- Redis caching functionality
- S3 client library
- TOML/JSON parsing libraries

### Code Quality Standards

- **Type hints**: All functions must have complete type hints
- **Docstrings**: All public functions, classes, and methods must have comprehensive docstrings
- **File headers**: Every file must start with "ABOUTME:" comment (2 lines max)
- **Error handling**: Fail fast with clear error messages
- **mypy --strict**: All code must pass strict type checking
- **ruff**: All code must pass linting with no errors
- **Coverage**: Maintain >= 80% test coverage

### Commit Strategy

- Make frequent, atomic commits
- Use conventional commit format: `feat:`, `test:`, `refactor:`, `docs:`, `fix:`
- Each step should result in 2-4 commits:
  - `test: add tests for [feature]` (RED)
  - `feat: implement [feature]` (GREEN)
  - `refactor: improve [feature]` (REFACTOR)
  - `docs: document [feature]`

---

## Success Metrics

### Functional Requirements
- [ ] Players can register via web form and receive unique IDs
- [ ] Daily questions load and display one at a time
- [ ] Answer submissions are validated and scored correctly
- [ ] Leaderboard displays all players with daily and total scores
- [ ] Tied players share same rank with proper next-rank adjustment
- [ ] Day buttons show correct state (active/inactive/completed)
- [ ] CSV exports generate and upload to S3 daily
- [ ] Multi-day events run without manual intervention

### Technical Requirements
- [ ] 80%+ test coverage across all modules
- [ ] All tests pass reliably (no flaky tests)
- [ ] Type checking passes with `mypy --strict`
- [ ] Linting passes with `ruff`
- [ ] Docker Compose stack runs successfully
- [ ] Works with both local Temporal and Temporal Cloud
- [ ] FastAPI serves HTMX responses correctly
- [ ] Redis caching reduces Temporal query load

### Documentation Requirements
- [ ] All API endpoints have comprehensive docstrings
- [ ] Workflow architecture documented
- [ ] How-to guides cover setup, deployment, event creation
- [ ] README provides quick-start instructions
- [ ] CLAUDE.md captures implementation learnings

### Performance Requirements
- [ ] Supports 1000+ concurrent players without degradation
- [ ] Leaderboard queries return within 2 seconds
- [ ] Answer submissions respond within 500ms
- [ ] Frontend pages load within 1 second on 3G connection

---

## Phase Dependencies

Each phase builds on previous phases:

1. **Phase 1 (Foundation)**: Sets up project structure and core models
2. **Phase 2 (Configuration)**: Builds configuration and question loading (depends on Phase 1)
3. **Phase 3 (Workflows)**: Implements workflows using models and activities (depends on Phases 1-2)
4. **Phase 4 (API)**: Creates API layer using workflows (depends on Phases 1-3)
5. **Phase 5 (Frontend)**: Adds UI and integration tests (depends on Phases 1-4)
6. **Phase 6 (Deployment)**: Adds deployment and documentation (depends on all previous phases)

No step can be started until its phase dependencies are complete.
