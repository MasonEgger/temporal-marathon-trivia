# Marathon Trivia Platform - Technical Specification

**Version**: 1.0
**Date**: 2025-11-25
**Purpose**: Trade show booth engagement platform for multi-day trivia competitions

## 1. Overview

### 1.1 Purpose
Marathon Trivia Platform is a web-based trivia application designed for trade show booth engagement. Players visit a booth daily to answer new trivia questions, accumulating scores across multiple days for prize eligibility. The platform supports hundreds to thousands of concurrent players in an asynchronous, self-paced format.

### 1.2 Key Characteristics
- **Web-only interaction** - no SMS, all gameplay through browser
- **Multi-day events** - configurable start/end dates with daily questions
- **Asynchronous progression** - each player moves at their own pace
- **Massive scale** - support 100s-1000s of concurrent players
- **Live leaderboard** - real-time rankings with daily and total scores
- **Simple deployment** - one deployment per event

### 1.3 Use Case
Trade show scenario: Booth staff deploy the platform for a 3-5 day conference. Attendees scan a QR code to join, answer questions daily, and compete for prizes. The leaderboard drives engagement and return visits.

## 2. Architecture

### 2.1 High-Level Components

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Browser   │─────▶│   FastAPI   │─────▶│  Temporal   │
│  (HTMX +    │◀─────│  REST API   │◀─────│  Workflows  │
│  Tailwind)  │      │  + Redis    │      │   (Python)  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   AWS S3    │
                     │ (CSV Export)│
                     └─────────────┘
```

### 2.2 Technology Stack
- **Backend**: Temporal Python SDK, FastAPI, Redis
- **Frontend**: HTMX, Alpine.js (if needed), Tailwind CSS
- **Deployment**: Docker Compose with Temporal single binary
- **Storage**: Filesystem → S3 for CSV exports
- **Configuration**: TOML for event config, .env for secrets

### 2.3 Temporal Workflow Architecture

**Entity Workflow Pattern**:
- **Event Workflow** (1 per event): Parent workflow managing the entire event lifecycle
- **Daily Child Workflows** (1 per day): Started when each day begins, maintains daily leaderboard
- **Player Entity Workflows** (1 per player): Persists player state across entire event

```
EventWorkflow (entire event)
├── DailyWorkflow (Day 1)
│   ├── receives score updates from players
│   └── maintains daily leaderboard
├── DailyWorkflow (Day 2)
└── DailyWorkflow (Day 3)

PlayerEntityWorkflow (per player)
├── tracks current question, score, progress
├── submits answers to DailyWorkflow
└── persists across all days
```

## 3. Data Models

### 3.1 Question Model
```python
@dataclass
class Question:
    """Multiple choice trivia question."""
    id: str
    text: str
    options: dict[str, str]  # {"A": "option1", "B": "option2", "C": "option3", "D": "option4"}
    correct_answer: str  # Key ("A", "B", "C", or "D") of correct option
```

### 3.2 Player Model
```python
@dataclass
class Player:
    """Player identity and state."""
    id: str  # UUID generated for entity workflow
    email: str  # Unique identifier
    first_name: str
    last_name: str
    total_score: int
    daily_scores: dict[str, int]  # {"2025-03-10": 5, "2025-03-11": 4}
    completed_days: set[str]  # ISO date strings
    current_question_index: dict[str, int]  # {"2025-03-10": 3}
```

### 3.3 Leaderboard Entry Model
```python
@dataclass
class LeaderboardEntry:
    """Leaderboard row for display."""
    rank: int
    display_name: str  # "John D."
    total_score: int
    daily_scores: dict[str, int]  # {"2025-03-10": 5, ...}
    email: str  # For "find my rank" functionality
```

### 3.4 Event Configuration Model
```python
@dataclass
class EventConfig:
    """Event configuration loaded from TOML."""
    # Event metadata
    title: str
    description: str
    base_url: str  # e.g., "trivia.ziggy.codes"

    # Dates and timing
    start_date: date
    end_date: date
    day_start_time: time  # e.g., 09:00
    day_end_time: time    # e.g., 17:00
    timezone: str  # e.g., "America/Los_Angeles"

    # Questions
    questions_file_path: str
    questions_per_day: int

    # UI messages
    completion_message: str
    day_over_message: str
    not_started_message: str
    already_completed_message: str

    # Colors (for Tailwind)
    primary_color: str
    secondary_color: str
    background_color: str
    text_color: str

    # Feature flags
    show_correct_answer: bool
    require_work_email: bool

    # S3
    s3_bucket_name: str
    s3_region: str
```

## 4. Configuration

### 4.1 TOML Configuration (`config/event.toml`)
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

[ui.messages]
completion = "Great job! You've completed today's questions. Come back tomorrow for more!"
day_over = "Today's trivia has ended. Check back tomorrow!"
not_started = "This day's trivia hasn't started yet. Check back later!"
already_completed = "You've already completed today's questions. Come back tomorrow!"

[ui.colors]
primary = "#3b82f6"
secondary = "#8b5cf6"
background = "#ffffff"
text = "#1f2937"

[features]
show_correct_answer = true
require_work_email = true

[s3]
bucket_name = "marathon-trivia-exports"
region = "us-west-2"
```

### 4.2 Environment Variables (`.env`)
Reference `temporal-trivia-python` for Temporal connection patterns:
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

## 5. Workflows

### 5.1 EventWorkflow (Parent)

**Purpose**: Manages the entire event lifecycle, starts daily child workflows.

**State**:
```python
@dataclass
class EventState:
    event_id: str
    config: EventConfig
    daily_workflow_ids: dict[str, str]  # {"2025-03-10": "workflow_id"}
    player_count: int
```

**Lifecycle**:
1. Loads event configuration from TOML
2. Validates questions file exists and is well-formed
3. Schedules timers to start each daily child workflow at day_start_time
4. Monitors daily workflows
5. Schedules end-of-day CSV export activities

**Update Handlers**:
- `register_player(email: str, first_name: str, last_name: str) -> str`: Creates player entity workflow, returns player ID

**Queries**:
- `get_event_status() -> dict`: Returns active days, player count, current day

**Activities**:
- `load_config() -> EventConfig`
- `validate_questions_file(path: str) -> None`
- `export_daily_csv(date: str, players: list[Player]) -> None`

### 5.2 DailyWorkflow (Child)

**Purpose**: Manages a single day's trivia, maintains daily leaderboard.

**State**:
```python
@dataclass
class DailyState:
    date: str  # ISO format "2025-03-10"
    questions: list[Question]
    player_scores: dict[str, int]  # {player_id: score}
    completed_players: set[str]
```

**Lifecycle**:
1. Started by EventWorkflow at day_start_time
2. Loads questions for this day
3. Receives score updates from player entity workflows
4. Maintains running leaderboard
5. At day_end_time, triggers CSV export via parent workflow

**Update Handlers**:
- `submit_score(player_id: str, score: int) -> None`: Updates daily leaderboard

**Queries**:
- `get_daily_leaderboard() -> list[LeaderboardEntry]`: Returns sorted leaderboard for this day
- `is_day_active() -> bool`: Checks if current time is within day hours

**Validation**:
- Reject score submissions if day hasn't started or has ended
- Reject duplicate score submissions from same player

### 5.3 PlayerEntityWorkflow

**Purpose**: Maintains per-player state across entire event.

**State**:
```python
@dataclass
class PlayerState:
    player: Player
    current_day: str | None
    current_question_index: int
```

**Lifecycle**:
- Long-running workflow (entire event duration)
- Persists player progress across all days
- Never completes until event ends

**Update Handlers**:
- `start_day(date: str) -> Question`: Begins a new day, returns first question
- `submit_answer(date: str, question_id: str, answer_index: int) -> AnswerResult`: Validates and scores answer, returns next question or completion message
- `get_player_progress() -> PlayerState`: Returns current state

**Queries**:
- `get_current_state() -> PlayerState`: Returns full player state
- `get_score_for_day(date: str) -> int`: Returns score for specific day
- `has_completed_day(date: str) -> bool`: Checks if player finished a day

**Validation**:
- Validate question_id exists for given date
- Validate answer_index is 0-3
- Prevent answering same question twice
- Prevent starting a day that hasn't started yet
- Prevent continuing a day that has ended
- Validate player hasn't already completed the day

**Activities Called**:
- `get_questions_for_day(date: str) -> list[Question]`
- `validate_email(email: str, require_work_email: bool) -> bool`

**Answer Validation**:
- Validate answer is one of ["A", "B", "C", "D"]
- Compare against question.correct_answer to determine correctness

## 6. Activities

### 6.1 Configuration Activities
```python
async def load_event_config(config_path: str) -> EventConfig:
    """Load and parse TOML configuration."""
    # Parse TOML, validate required fields, return EventConfig

async def validate_questions_file(file_path: str) -> None:
    """Ensure questions file exists and is valid JSON."""
    # Raise error if missing or malformed (fail fast at startup)
```

### 6.2 Question Activities
```python
async def load_questions(file_path: str) -> dict[str, list[Question]]:
    """Load all questions from JSON file."""
    # Returns: {"2025-03-10": [Question(...), ...], ...}

async def get_questions_for_day(file_path: str, date: str) -> list[Question]:
    """Get questions for a specific day."""
    # Returns subset based on date key
```

### 6.3 Email Validation Activity
```python
async def validate_email(email: str, require_work_email: bool) -> bool:
    """Validate email format and optionally block consumer domains."""
    # Block: gmail.com, yahoo.com, hotmail.com, outlook.com, etc.
    # Return False if invalid or blocked, True otherwise
```

### 6.4 Export Activities
```python
async def export_daily_csv_to_s3(
    bucket: str,
    region: str,
    date: str,
    players: list[Player]
) -> str:
    """Export daily player data to S3 as CSV."""
    # Filename: "marathon-trivia-{date}.csv"
    # Returns: S3 URL
```

## 7. API Layer (FastAPI)

### 7.1 Endpoints

All endpoints return HTML fragments for HTMX (not JSON).

#### 7.1.1 Player Management
```python
POST /api/join
Request: <form> with first_name, last_name, email
Response: HTML fragment with player_id cookie set and redirect to main page
Validation:
  - Email format
  - Work email (if required)
  - Duplicate email → redirect to existing player

GET /api/player
Response: HTML fragment with player's current state (for "find my rank")
```

#### 7.1.2 Gameplay
```python
GET /api/day/{date}/start
Response: HTML fragment with first question
Validation:
  - Day has started
  - Day hasn't ended
  - Player hasn't completed day

POST /api/day/{date}/answer
Request: <form> with question_id, answer_choice (A/B/C/D)
Response: HTML fragment with:
  - Correct/incorrect feedback (if show_correct_answer enabled)
  - Next question OR completion message
Validation:
  - Question exists
  - Answer choice is one of ["A", "B", "C", "D"]
  - Day is active
  - Player hasn't completed day

GET /api/day/{date}/status
Response: HTML fragment with day button state (active/completed/inactive)
```

#### 7.1.3 Leaderboard
```python
GET /api/leaderboard
Response: HTML table fragment with leaderboard
Cache: 30 seconds in Redis
Query: Aggregates from all DailyWorkflows
```

#### 7.1.4 Configuration
```python
GET /api/config
Response: JSON with event title, description, dates, colors
Cache: Startup (config doesn't change during event)
```

#### 7.1.5 Health
```python
GET /health
Response: {"status": "ok"}
```

### 7.2 Caching Strategy (Redis)

**Leaderboard Cache**:
- Key: `leaderboard:full`
- TTL: 30 seconds
- On miss: Query all DailyWorkflows, aggregate, cache

**Player State Cache**:
- Key: `player:{player_id}:state`
- TTL: 10 seconds
- On miss: Query PlayerEntityWorkflow

**Config Cache**:
- Key: `config:event`
- TTL: None (loaded at startup, never expires)

### 7.3 CORS and Security
- Only allow same-origin requests (frontend served from same domain)
- Set CORS headers to block external API access
- HTMX endpoints return HTML, not JSON (discourages external use)

## 8. Frontend

### 8.1 Technology
- **HTMX**: Dynamic content loading without JavaScript
- **Tailwind CSS**: Utility-first styling, colors from config
- **Alpine.js**: Only if absolutely necessary for interactivity
- **Templates**: Server-rendered HTML via FastAPI

### 8.2 Pages

#### 8.2.1 Landing Page (`/`)
**First-time visitor**:
```html
<div>
  <h1>{event.title}</h1>
  <p>{event.description}</p>
  <form hx-post="/api/join" hx-target="#main">
    <input name="first_name" placeholder="First Name" required>
    <input name="last_name" placeholder="Last Name" required>
    <input name="email" type="email" placeholder="Email" required>
    <button type="submit">Join Now</button>
  </form>
</div>
```

**Returning player** (has player_id cookie):
```html
<div>
  <h1>{event.title}</h1>

  <!-- Day buttons -->
  <div class="day-buttons">
    <button hx-get="/api/day/2025-03-10/start" disabled>Day 1 (Past)</button>
    <button hx-get="/api/day/2025-03-11/start">Day 2 (Play Now)</button>
    <button hx-get="/api/day/2025-03-12/start" disabled>Day 3 (Coming Soon)</button>
  </div>

  <!-- Leaderboard -->
  <div hx-get="/api/leaderboard" hx-trigger="load, every 30s">
    <!-- Leaderboard table loaded here -->
  </div>

  <!-- Find My Rank button -->
  <button hx-get="/api/player" hx-target="#leaderboard">Find My Rank</button>
</div>
```

#### 8.2.2 Question Page (`/play`)
**Single question display**:
```html
<div>
  <h2>Question {current}/{total}</h2>
  <p>{question.text}</p>

  <form hx-post="/api/day/{date}/answer" hx-target="#question-container">
    <input type="hidden" name="question_id" value="{question.id}">

    <label>
      <input type="radio" name="answer_choice" value="A" required>
      A. {question.options["A"]}
    </label>
    <label>
      <input type="radio" name="answer_choice" value="B">
      B. {question.options["B"]}
    </label>
    <label>
      <input type="radio" name="answer_choice" value="C">
      C. {question.options["C"]}
    </label>
    <label>
      <input type="radio" name="answer_choice" value="D">
      D. {question.options["D"]}
    </label>

    <button type="submit">Submit Answer</button>
  </form>
</div>
```

**After answer submission** (if `show_correct_answer: true`):
```html
<div>
  <p class="correct">✓ Correct!</p>  <!-- or "✗ Incorrect. The answer was: {correct_option}" -->
  <button hx-get="/api/day/{date}/next" hx-target="#question-container">
    Next Question
  </button>
</div>
```

**Day completion**:
```html
<div>
  <h2>Day Complete!</h2>
  <p>Your score: {score}/{total}</p>
  <p>{config.completion_message}</p>
  <a href="/" hx-get="/" hx-target="body">Back to Leaderboard</a>
</div>
```

### 8.3 Leaderboard Table
```html
<table>
  <thead>
    <tr>
      <th>Rank</th>
      <th>Player</th>
      <th>Total</th>
      <th>Day 1</th>
      <th>Day 2</th>
      <th>Day 3</th>
    </tr>
  </thead>
  <tbody>
    <!-- Rank 1 (multiple tied players) -->
    <tr class="rank-1">
      <td>1</td>
      <td>John D.</td>
      <td>15</td>
      <td>5</td>
      <td>5</td>
      <td>5</td>
    </tr>
    <tr class="rank-1">
      <td>1</td>
      <td>Jane S.</td>
      <td>15</td>
      <td>5</td>
      <td>5</td>
      <td>5</td>
    </tr>
    <!-- Next rank is 3, not 2 -->
    <tr class="rank-3">
      <td>3</td>
      <td>Bob M.</td>
      <td>14</td>
      <td>5</td>
      <td>4</td>
      <td>5</td>
    </tr>
  </tbody>
</table>

<!-- Search box -->
<input
  type="search"
  placeholder="Find your name..."
  hx-get="/api/leaderboard/search"
  hx-trigger="keyup changed delay:500ms"
  hx-target="#leaderboard-table"
>
```

### 8.4 Styling (Tailwind)
- Colors injected from `event.toml` via CSS variables
- Responsive design (mobile-first)
- Minimal, clean aesthetic suitable for trade show displays
- High contrast for readability on booth screens

## 9. Error Handling

### 9.1 Validation Rules

**Player Registration**:
- Email format: Standard RFC 5322 validation
- Work email validation (if enabled): Block consumer domains (gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com, icloud.com)
- Duplicate email: Redirect to existing player (no error)

**Answer Submission**:
- Day not started: Return HTML fragment with `not_started_message`
- Day ended: Return HTML fragment with `day_over_message`
- Already completed day: Return HTML fragment with `already_completed_message`
- Invalid question_id: Return error HTML fragment (shouldn't happen in normal flow)
- Invalid answer_choice: Return error HTML fragment (must be A, B, C, or D)

**Startup Validation**:
- Missing questions file: **Fail fast** with error log, exit application
- Malformed TOML: **Fail fast** with error log, exit application
- Invalid date ranges: **Fail fast** with error log, exit application

### 9.2 Workflow Error Handling

**Entity Workflow Corruption**:
- **Manual recovery required** (acceptable for trade show use case)
- Log error details for operator intervention
- No automatic retry/recreation (prevents duplicate players)

**Activity Failures**:
- S3 upload failure: Retry 3 times with exponential backoff, then log error
- Config/question loading: Fail immediately, propagate to workflow
- Email validation: Return False on error (graceful degradation)

### 9.3 API Error Responses

All errors return HTML fragments (not JSON) suitable for HTMX:
```html
<div class="error">
  <p>{error_message}</p>
  <button hx-get="/" hx-target="body">Back to Home</button>
</div>
```

## 10. Testing Strategy

### 10.1 Coverage Requirements
- **Minimum 80% code coverage** across all modules
- Focus on testing **application logic**, not framework behavior

### 10.2 Patterns to Reuse from `temporal-trivia-python`

**Critical patterns learned**:
1. **Update handlers**: Test that updates return correct responses immediately
2. **Continue-as-new**: Use positional args for explicit state passing
3. **Time-skipping tests**: Use `asyncio.sleep()` after signals for processing
4. **Class-based activities with Protocol DI**: Enable clean testing and mocking
5. **Defensive queries**: Return `.copy()` to prevent external mutation
6. **Temporal test environment setup**: Reuse fixtures and patterns

### 10.3 Test Categories

#### Unit Tests
**Workflows**:
- `test_event_workflow_creates_daily_children()`
- `test_daily_workflow_maintains_leaderboard()`
- `test_player_entity_workflow_tracks_progress()`
- `test_player_workflow_rejects_duplicate_answers()`
- `test_daily_workflow_rejects_late_submissions()`
- `test_player_workflow_validates_answer_choice()` (must be A/B/C/D)

**Activities**:
- `test_load_event_config_parses_toml()`
- `test_validate_questions_file_raises_on_missing()`
- `test_validate_email_blocks_consumer_domains()`
- `test_export_csv_formats_correctly()`

**Business Rules**:
- `test_leaderboard_ranking_with_ties()`
- `test_leaderboard_alphabetical_tie_breaking()`
- `test_scoring_one_point_per_question()`
- `test_player_display_name_formatting()` (first name + last initial)

#### Integration Tests
- `test_full_player_journey()`: Join → Answer all questions → See leaderboard
- `test_multi_day_score_accumulation()`: Complete day 1, then day 2, verify total
- `test_duplicate_email_redirects_to_existing_player()`
- `test_leaderboard_query_aggregates_all_days()`

#### End-to-End Tests
- `test_complete_event_lifecycle()`: Event starts → Players join → Play multiple days → Export CSVs
- `test_time_based_day_transitions()`: Verify daily workflows start/stop at configured times

### 10.4 Test Data
- **Fixture questions**: Minimal set (5 questions × 3 days)
- **Fixture config**: Complete but minimal TOML
- **Mock S3**: Use moto or similar for S3 testing
- **Mock Redis**: Use fakeredis for caching tests

## 11. Data Formats

### 11.1 Questions JSON (`config/questions.json`)
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
    },
    {
      "id": "q2",
      "text": "Which AWS service is used for object storage?",
      "options": {
        "A": "EBS",
        "B": "S3",
        "C": "RDS",
        "D": "DynamoDB"
      },
      "correct_answer": "B"
    }
  ],
  "2025-03-11": [
    {
      "id": "q3",
      "text": "What is the maximum size of an S3 object?",
      "options": {
        "A": "5 GB",
        "B": "50 GB",
        "C": "5 TB",
        "D": "Unlimited"
      },
      "correct_answer": "C"
    }
  ]
}
```

**Schema validation at startup**:
- All dates in config.event.start_date to end_date must have entries
- Each day must have exactly `config.questions.per_day` questions
- Each question must have exactly 4 options with keys ["A", "B", "C", "D"]
- `correct_answer` must be one of ["A", "B", "C", "D"]

### 11.2 CSV Export Format

**Filename**: `marathon-trivia-{date}.csv`

**Columns**:
```csv
email,first_name,last_name,total_score,day1_score,day2_score,day3_score,completed_days
john@example.com,John,Doe,15,5,5,5,3
jane@example.com,Jane,Smith,14,5,4,5,3
bob@company.com,Bob,Miller,10,5,5,0,2
```

**Rules**:
- One row per player (all players, not just active)
- Day columns are dynamic based on event dates
- `completed_days`: Count of days where player answered at least 1 question
- Generated at end of each day (via EventWorkflow activity)
- Uploaded to S3 immediately after generation

## 12. Deployment

### 12.1 Docker Compose (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=sqlite
      - SQLITE_PRAGMA_journal_mode=WAL

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  worker:
    build: .
    depends_on:
      - temporal
      - redis
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
      - TEMPORAL_NAMESPACE=default
      - TEMPORAL_TASK_QUEUE=marathon-trivia
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    command: python src/worker.py

  api:
    build: .
    depends_on:
      - temporal
      - redis
      - worker
    ports:
      - "8000:8000"
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
      - TEMPORAL_NAMESPACE=default
      - TEMPORAL_TASK_QUEUE=marathon-trivia
      - REDIS_URL=redis://redis:6379
      - API_HOST=0.0.0.0
      - API_PORT=8000
    volumes:
      - ./config:/app/config
      - ./frontend:/app/frontend
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 12.2 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ src/
COPY frontend/ frontend/

CMD ["python", "src/worker.py"]
```

### 12.3 Local Development (Non-Containerized)

**Prerequisites**:
- Python 3.11+
- Temporal CLI (`brew install temporal` or download)
- Redis (`brew install redis`)

**Setup**:
```bash
# Start Temporal dev server
temporal server start-dev

# Start Redis
redis-server

# Install dependencies
uv sync

# Run worker
uv run python src/worker.py

# Run API (separate terminal)
uv run uvicorn src.api.main:app --reload
```

### 12.4 Temporal Cloud Deployment

**Environment variables**:
```bash
TEMPORAL_ADDRESS=namespace.account.tmprl.cloud:7233
TEMPORAL_NAMESPACE=namespace.account
TEMPORAL_TLS_CERT_PATH=/path/to/cert.pem
TEMPORAL_TLS_KEY_PATH=/path/to/key.pem
```

**Connection code** (reference `temporal-trivia-python`):
```python
client = await Client.connect(
    os.environ["TEMPORAL_ADDRESS"],
    namespace=os.environ["TEMPORAL_NAMESPACE"],
    tls=TLSConfig(
        client_cert=Path(os.environ["TEMPORAL_TLS_CERT_PATH"]).read_bytes(),
        client_private_key=Path(os.environ["TEMPORAL_TLS_KEY_PATH"]).read_bytes(),
    ),
)
```

## 13. Documentation

### 13.1 API Documentation (`docs/api/`)

**Files to create**:
- `endpoints.md`: Complete endpoint reference with request/response examples
- `workflows.md`: Workflow architecture, state diagrams, update handlers, queries
- `activities.md`: Activity descriptions, parameters, return values
- `data-models.md`: Dataclass definitions, validation rules

**FastAPI OpenAPI**:
- All endpoints must have comprehensive docstrings
- FastAPI auto-generates interactive docs at `/docs` and `/redoc`

### 13.2 How-To Guides (`docs/how-to/`)

**Files to create**:
- `setup.md`: Local development setup, environment configuration
- `deployment.md`: Docker Compose deployment, Temporal Cloud setup
- `create-event.md`: How to configure a new event (TOML + questions JSON)
- `monitoring.md`: How to monitor workflows, check logs, access CSVs
- `troubleshooting.md`: Common issues and solutions

### 13.3 Code Documentation

**Docstring requirements**:
- All public functions/methods: Full docstring with params, returns, raises
- All workflows: Document state, update handlers, queries
- All activities: Document purpose, parameters, failure modes
- All dataclasses: Document field meanings and constraints

**File headers**:
```python
# ABOUTME: This file implements the PlayerEntityWorkflow for per-player state management.
# It handles answer submissions, score tracking, and progress queries.
```

## 14. Project Structure

```
temporal-marathon-trivia/
├── config/
│   ├── event.toml              # Event configuration
│   ├── event.example.toml      # Example config for reference
│   ├── questions.json          # Questions keyed by date
│   └── questions.example.json  # Example questions
│
├── src/
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── event.py            # EventWorkflow
│   │   ├── daily.py            # DailyWorkflow
│   │   └── player.py           # PlayerEntityWorkflow
│   │
│   ├── activities/
│   │   ├── __init__.py
│   │   ├── config.py           # Config loading/validation
│   │   ├── questions.py        # Question loading
│   │   ├── email.py            # Email validation
│   │   └── export.py           # CSV export to S3
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── question.py         # Question dataclass
│   │   ├── player.py           # Player, PlayerState dataclasses
│   │   ├── config.py           # EventConfig dataclass
│   │   └── leaderboard.py      # LeaderboardEntry dataclass
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── player.py       # Player endpoints
│   │   │   ├── gameplay.py     # Gameplay endpoints
│   │   │   └── leaderboard.py  # Leaderboard endpoints
│   │   ├── cache.py            # Redis caching logic
│   │   └── templates.py        # HTML template rendering
│   │
│   └── worker.py               # Temporal worker entry point
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css      # Additional custom CSS if needed
│   │   └── js/
│   │       └── htmx.min.js     # HTMX library
│   │
│   └── templates/
│       ├── base.html           # Base template with Tailwind
│       ├── landing.html        # Landing/main page
│       ├── question.html       # Question display
│       ├── leaderboard.html    # Leaderboard table
│       └── components/
│           ├── day-button.html
│           ├── answer-feedback.html
│           └── error.html
│
├── tests/
│   ├── unit/
│   │   ├── test_workflows.py
│   │   ├── test_activities.py
│   │   ├── test_models.py
│   │   └── test_api.py
│   │
│   ├── integration/
│   │   ├── test_player_journey.py
│   │   ├── test_leaderboard.py
│   │   └── test_multi_day.py
│   │
│   └── fixtures/
│       ├── config.toml
│       ├── questions.json
│       └── players.py
│
├── docs/
│   ├── api/
│   │   ├── endpoints.md
│   │   ├── workflows.md
│   │   ├── activities.md
│   │   └── data-models.md
│   │
│   └── how-to/
│       ├── setup.md
│       ├── deployment.md
│       ├── create-event.md
│       ├── monitoring.md
│       └── troubleshooting.md
│
├── docker-compose.yml          # Docker Compose for local dev
├── Dockerfile                  # Container image
├── pyproject.toml              # Python dependencies (uv)
├── uv.lock                     # Locked dependencies
├── Justfile                    # Common development tasks
├── .env.example                # Example environment variables
├── .gitignore
├── README.md                   # Project overview
└── CLAUDE.md                   # Claude-specific dev notes
```

## 15. Development Workflow

### 15.1 Justfile Commands

Reference `temporal-trivia-python` for task patterns:

```make
# Development
dev: Start all services (Temporal, Redis, worker, API)
worker: Run Temporal worker
api: Run FastAPI dev server with reload

# Testing
test: Run all tests with pytest
test-unit: Run unit tests only
test-integration: Run integration tests only
coverage: Run tests with coverage report

# Linting
lint: Run ruff linter
format: Run ruff formatter
typecheck: Run mypy type checker

# Docker
build: Build Docker image
up: Start Docker Compose stack
down: Stop Docker Compose stack

# Data
export-csv: Manually trigger CSV export for today
validate-config: Validate TOML and questions JSON
```

### 15.2 Development Workflow (TDD)

**For each feature**:
1. Write failing test(s) that define desired behavior
2. Run tests to confirm they fail
3. Write minimal code to make tests pass
4. Run tests to confirm success
5. Refactor while keeping tests green
6. Repeat

**Example TDD cycle for player entity workflow**:
1. `test_player_workflow_tracks_score()` → Write test, watch it fail
2. Implement `PlayerEntityWorkflow.submit_answer()` → Test passes
3. `test_player_workflow_rejects_duplicate_answer()` → Write test, watch it fail
4. Add validation logic → Test passes
5. Refactor state management → Tests still pass

### 15.3 Git Workflow

- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`
- **NEVER use `--no-verify`** when committing (respect pre-commit hooks)
- Keep commits focused and atomic
- Write descriptive commit messages explaining "why", not "what"

## 16. Success Criteria

This specification is complete and implementation-ready when:

### 16.1 Functional Requirements
- [ ] Players can join via web form, receive unique ID
- [ ] Daily questions load and display one at a time
- [ ] Answer submissions are validated and scored correctly
- [ ] Leaderboard displays all players with daily and total scores
- [ ] Tied players share same rank, next rank adjusts correctly
- [ ] Day buttons show correct state (active/inactive/completed)
- [ ] CSV exports generate and upload to S3 daily
- [ ] Multi-day events run without manual intervention

### 16.2 Technical Requirements
- [ ] 80%+ test coverage across all modules
- [ ] All tests pass reliably (no flaky tests)
- [ ] Type checking passes with `mypy --strict`
- [ ] Linting passes with `ruff`
- [ ] Docker Compose stack runs successfully
- [ ] Works with both local Temporal and Temporal Cloud
- [ ] FastAPI serves HTMX responses correctly
- [ ] Redis caching reduces Temporal query load

### 16.3 Documentation Requirements
- [ ] All API endpoints have comprehensive docstrings
- [ ] Workflow architecture documented with diagrams
- [ ] How-to guides cover setup, deployment, event creation
- [ ] README provides quick-start instructions
- [ ] CLAUDE.md captures implementation learnings

### 16.4 Performance Requirements
- [ ] Supports 1000+ concurrent players without degradation
- [ ] Leaderboard queries return within 2 seconds
- [ ] Answer submissions respond within 500ms
- [ ] Frontend pages load within 1 second on 3G connection

## 17. Open Questions and Future Enhancements

### 17.1 Deferred Features (Out of Scope for v1)
- LLM question generation (use static JSON for now)
- Admin UI for event management
- Multi-event support in single deployment
- Player authentication/accounts
- Real-time leaderboard updates (WebSockets)
- Mobile app
- Analytics dashboard
- Prize management integration

### 17.2 Questions for Future Discussion
- **Multi-day scoring strategy**: Should we use workflow search aggregation for historical events?
- **Scale target verification**: Have we tested with 1000+ concurrent players?
- **Question pool management**: How to rotate questions for recurring events?
- **Leaderboard pagination**: If 5000+ players, do we need pagination?
- **Internationalization**: Support for non-English questions?

## 18. References

### 18.1 Existing Codebases
- **temporal-trivia-python**: Sprint trivia app, reuse testing patterns, config patterns, workflow structure
- **temporal-trivia-frontend**: SvelteKit frontend (for comparison, not reuse)
- **durable-wordle**: Entity workflow pattern reference

### 18.2 External Documentation
- Temporal Python SDK: https://docs.temporal.io/dev-guide/python
- FastAPI: https://fastapi.tiangolo.com/
- HTMX: https://htmx.org/
- Tailwind CSS: https://tailwindcss.com/

---

**End of Specification**

This document provides a complete technical specification for implementing the Marathon Trivia Platform. All architectural decisions, data models, component boundaries, and testing requirements are defined. The specification is ready for conversion into an implementation plan and TDD-driven development.
