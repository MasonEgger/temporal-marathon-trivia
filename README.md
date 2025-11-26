# Marathon Trivia Platform

A multi-day, web-based trivia application built with Temporal workflows, designed for trade show booth engagement. Players answer daily questions at their own pace, competing on a live leaderboard for prizes.

**Built for**: AWS re:Invent 2025 (and similar conferences)

**Tech Stack**: Temporal Python SDK, FastAPI, HTMX, Tailwind CSS, Redis

## Quick Start (5 Minutes)

### Prerequisites

- Python 3.14+
- Temporal CLI ([installation guide](https://docs.temporal.io/cli#install))
- Redis ([installation guide](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-stack/mac-os/))
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

### 1. Install Dependencies

```bash
# Clone the repository (if not already done)
cd temporal-marathon-trivia

# Install dependencies
uv sync --extra dev
```

### 2. Configure Your Event

Edit `config/event.toml` with your event details. The configuration is split into two sections:
- **Business Logic** (`[event]`, `[dates]`, `[features]`, etc.) - Controls workflow behavior
- **UI/Presentation** (`[ui.*]`) - Controls appearance and messaging

```toml
# Business Logic Configuration
[event]
title = "AWS re:Invent 2025 Trivia"  # Legacy - kept for backwards compatibility
description = "Test your cloud knowledge and win prizes!"
base_url = "trivia.example.com"

[dates]
start_date = "2025-12-01"  # YYYY-MM-DD format (event first day)
end_date = "2025-12-05"    # YYYY-MM-DD format (event last day, inclusive)
day_start_time = "09:00:00"  # HH:MM:SS (when daily questions become available)
day_end_time = "17:00:00"    # HH:MM:SS (when daily questions close)
timezone = "America/Los_Angeles"  # IANA timezone (e.g., America/New_York, UTC)

[questions]
file_path = "config/questions.json"  # Path to questions JSON file
per_day = 10  # Number of questions per day (must match questions.json)

[features]
show_correct_answer = true   # Show correct answer after submission
require_work_email = true    # Block consumer email domains (gmail, yahoo, etc.)

[s3]
bucket_name = "marathon-trivia-exports"  # S3 bucket for CSV exports
region = "us-west-2"  # AWS region

# UI/Presentation Configuration
[ui.branding]
title = "Temporal re:Invent 2025 Trivia"  # Displayed on landing page
description = "Test your tech knowledge and win prizes!"  # Subtitle text
base_url = "trivia.ziggy.codes"  # Your domain (for display purposes)

[ui.messages]
completion_message = "🎉 Great job! Check the leaderboard to see your ranking."
day_over_message = "⏰ Today's trivia has ended. Come back tomorrow!"
not_started_message = "📅 This day's trivia hasn't started yet."
already_completed_message = "✅ You've already completed today's trivia!"
invalid_work_email_message = "⚠️ Please use your work email address. Personal email domains (gmail, yahoo, etc.) are not permitted for this event."

[ui.colors]
primary_color = "#444CD1"      # Primary brand color (hex)
secondary_color = "#141414"    # Secondary brand color (hex)
background_color = "#F8FAFC"   # Page background (hex)
text_color = "#232F3E"         # Text color (hex)

[ui.performance]
leaderboard_refresh_seconds = 5  # How often leaderboard auto-refreshes (default: 30)
```

**Configuration Tips:**

- **Email Validation**: Set `require_work_email = true` for corporate events to block gmail/yahoo/hotmail
- **Blocked Domains**: gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com, icloud.com
- **Leaderboard Refresh**:
  - 5s = Super responsive (demo/trade show)
  - 10s = Fast refresh
  - 30s = Conservative (default, lower server load)
- **Colors**: Use your brand colors for primary/secondary
- **Messages**: All user-facing text is configurable - customize for your event!

Edit `config/questions.json` with your trivia questions:

```json
{
  "2025-12-01": [
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

**Important**: Add questions for each day in your event date range (start_date to end_date).

### 3. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Temporal connection
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=marathon-trivia
EVENT_WORKFLOW_ID=marathon-trivia-event

# Event configuration
EVENT_CONFIG_PATH=config/event.toml

# Redis
REDIS_URL=redis://localhost:6379

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000

# AWS credentials (for CSV export - optional for demo)
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
```

### 4. Start Services

Open **four terminal windows**:

**Terminal 1 - Temporal Dev Server:**
```bash
temporal server start-dev
```

**Terminal 2 - Redis:**
```bash
redis-server
```

**Terminal 3 - Temporal Worker:**
```bash
uv run python src/worker.py
```

You should see:
```
================================================================================
Marathon Trivia Platform - Temporal Worker
================================================================================
Task Queue: marathon-trivia
Temporal Address: localhost:7233
🚀 Worker started successfully!
```

**Terminal 4 - FastAPI Server:**
```bash
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Initialize the Event

Run the startup script to create the EventWorkflow instance:

```bash
uv run python scripts/start_event.py
```

Expected output:
```
✅ Event workflow started: marathon-trivia-event
📅 Daily workflows will be scheduled for 5 days
🎮 Platform is ready for players!
```

### 6. Open the Application

```bash
open http://localhost:8000
```

Or visit: `http://localhost:8000` in your browser.

## Configuration Reference

### Resume Functionality

**Players can close their browser mid-session and resume later!**

The system tracks:
- Current question index (where player left off)
- Daily score accumulated so far
- Questions loaded for the day

**How it works:**
1. Player answers questions 1-3, closes browser
2. Player returns hours later, clicks day button
3. Button shows **"▶ Resume"** (orange, pulsing animation)
4. Player continues from question 4 (not question 1!)
5. Score and progress are preserved via Temporal's durable state

**Day boundaries**: Once the day ends (`day_end_time`), the workflow completes and resume is no longer possible.

### Email Validation

When `require_work_email = true`:
- **Blocked domains**: gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com, icloud.com
- **UX**: Shows yellow warning (not red error) with configurable message
- **Customization**: Edit `invalid_work_email_message` in `[ui.messages]`

**Visual distinction:**
- 🟡 **Warning** (yellow): Business rule validation (work email required, already registered)
- 🔴 **Error** (red): System failures (network error, workflow not found)

### Leaderboard Refresh

Controlled by single config value: `leaderboard_refresh_seconds` in `[ui.performance]`

**What it controls:**
1. **Frontend polling**: HTMX auto-refresh interval
2. **Backend caching**: Redis TTL (synchronized)
3. **Server load**: Lower values = more frequent queries

**Recommended values:**
- **5s**: Trade show kiosks, demos (high engagement, visible updates)
- **10s**: Fast refresh, moderate load
- **30s**: Conservative, lower server load (default)

### Color Customization

All colors support **hex format** (`#RRGGBB`):

```toml
[ui.colors]
primary_color = "#444CD1"      # Buttons, headings, accents
secondary_color = "#141414"    # Secondary buttons, borders
background_color = "#F8FAFC"   # Page background
text_color = "#232F3E"         # Body text
```

**Trade show tips:**
- High contrast for visibility (light backgrounds work best)
- Bold primary colors for brand recognition
- Test on projector/kiosk screen before event

## Using the Application

### Player Journey

1. **Registration**: Enter first name, last name, and email
   - If work email required: Rejected emails show friendly yellow warning (not error)
2. **Select Day**: Click on day button
   - **Green "✓ Completed"**: Already finished
   - **Orange "▶ Resume"**: In-progress, can continue from where you left off
   - **Blue "🎮 Play Now"**: Available to start
   - **Gray "🔒 Not Available"**: Future/past days
3. **Answer Questions**: Choose A/B/C/D for each question
4. **View Results**: See your score and correct answers (if `show_correct_answer = true`)
5. **Check Leaderboard**: Auto-refreshes every 5-30 seconds (configurable)

### Admin Operations

**View Event Status:**
```bash
temporal workflow describe --workflow-id marathon-trivia-event
```

**Query Player State:**
```bash
# Get player's workflow ID from the UI cookie or database
temporal workflow query \
  --workflow-id marathon-trivia-event-player-{email-hash} \
  --query-type get_current_state
```

**Export Daily Leaderboard CSV:**
```bash
# This happens automatically at end of day
# Manual trigger via workflow update (future feature)
```

## Development Commands

```bash
# Run all checks (lint + typecheck + test)
just check

# Run tests
just test                    # All tests with coverage
just test-unit              # Unit tests only
just test-integration       # Integration tests only

# Code quality
just lint                   # Run ruff linter
just format                 # Format code with ruff
just typecheck              # Run mypy --strict

# Run single test file
uv run pytest tests/unit/test_models.py -v

# Run single test case
uv run pytest tests/unit/test_workflows.py::TestPlayerEntityWorkflow::test_start_day -v
```

## Troubleshooting

### Worker Won't Start

**Problem**: `ImportError` or module not found

**Solution**: Install dependencies
```bash
uv sync --extra dev
```

### EventWorkflow Not Found

**Problem**: API returns "Workflow not found"

**Solution**: Run the initialization script
```bash
uv run python scripts/start_event.py
```

### Redis Connection Error

**Problem**: `ConnectionError: Error 61 connecting to localhost:6379`

**Solution**: Start Redis
```bash
redis-server
```

### Questions Validation Failed

**Problem**: "Questions file validation failed"

**Solution**: Check that `config/questions.json` has questions for ALL days in your event date range.

```bash
# Validate manually
uv run python -c "
from src.activities.config import ConfigActivities
from src.activities.questions import QuestionsActivities

config_activities = ConfigActivities()
questions_activities = QuestionsActivities()

config = config_activities.load_event_config('config/event.toml')
questions_activities.validate_questions_file('config/questions.json', config)
print('✅ Configuration valid!')
"
```

### Player Registration Shows "Work Email Required"

**Behavior**: Yellow warning screen (not red error) when using gmail/yahoo/etc. with `require_work_email = true`

**This is expected!** The warning shows:
- ⚠️ Yellow "Notice" card
- Configurable message from `[ui.messages].invalid_work_email_message`
- "🔙 Try Again" button

**Solutions**:
1. Use a work/corporate email address
2. Or set `require_work_email = false` in `config/event.toml`

**Blocked domains**: gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com, icloud.com

### Leaderboard Not Updating

**Problem**: Leaderboard shows old data

**Solution**: Check refresh interval in `config/event.toml`:
```toml
[ui.performance]
leaderboard_refresh_seconds = 5  # Adjust as needed
```

Or clear Redis cache:
```bash
redis-cli FLUSHALL
```

**Note**: If you change `leaderboard_refresh_seconds`, restart the API server to pick up the change.

### Port Already in Use

**Problem**: `Error: Address already in use`

**Solution**: Change port or kill existing process
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uv run uvicorn src.api.main:app --reload --port 8001
```

## Architecture Overview

### Temporal Workflows

```
EventWorkflow (parent, entire event)
├── DailyWorkflow (child, per day)
│   └── Maintains daily leaderboard state
└── PlayerEntityWorkflow (child, per player)
    └── Tracks player progress and scores
```

**Key Pattern**: Entity workflows run indefinitely, allowing players to progress asynchronously. Daily workflows aggregate scores without querying thousands of player workflows.

### API Endpoints

- `GET /` - Landing page (registration or game interface)
- `POST /api/join` - Register new player
- `GET /api/day/{date}/start` - Start a day, get first question
- `POST /api/day/{date}/answer` - Submit answer, get next question
- `GET /api/leaderboard` - View ranked leaderboard
- `GET /api/player` - View leaderboard with your rank highlighted
- `GET /api/config` - Get event configuration (for frontend)

### Caching Strategy

- **Leaderboard**: Configurable TTL (matches frontend polling interval from `[ui.performance]`)
- **Player state**: 10s TTL
- **Config**: Permanent (loaded at startup)

**Note**: Leaderboard refresh interval is synchronized across:
1. Frontend HTMX polling (`hx-trigger="every Xs"`)
2. Redis cache expiration (`ex=X`)
3. Single config value: `leaderboard_refresh_seconds` in `event.toml`

## Known Limitations

### Scale Constraint (~2000 Players)

**Current architecture has a hard limit of ~2000 concurrent players** due to Temporal's child workflow restrictions.

- ✅ **Works for**: Trade show demos, small conferences (<2000 players)
- ⚠️ **Requires refactoring for**: Large conferences (50,000+ attendees)

**Workaround**: Deploy multiple EventWorkflow instances (sharding) if needed.

See `CLAUDE.md` section "Known Limitations and Future Architecture" for detailed refactoring plan.

## Testing

```bash
# Run all tests with coverage report
just test

# Coverage should be 80%+
# View detailed coverage report
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

### Test Categories

- **Unit Tests** (`tests/unit/`): Individual workflows, activities, models, API endpoints
- **Integration Tests** (`tests/integration/`): Full player journeys, multi-day flows, leaderboard aggregation

### Testing Philosophy

- Focus on **application logic only** (not framework behavior)
- DO NOT test Redis/Temporal SDK operations
- DO test business rules, validation, scoring, ranking

## Deployment (Production)

### Temporal Cloud

1. Update `.env` with Temporal Cloud credentials:

```bash
TEMPORAL_ADDRESS=<namespace>.tmprl.cloud:7233
TEMPORAL_NAMESPACE=<namespace>
TEMPORAL_TLS_CERT=/path/to/client.pem
TEMPORAL_TLS_KEY=/path/to/client.key
```

2. Start worker (same command):

```bash
uv run python src/worker.py
```

**No code changes required** - connection utility detects TLS credentials automatically!

### Docker Deployment

```bash
# Build image
docker build -t marathon-trivia:latest .

# Run with docker-compose
docker-compose up -d
```

(Docker configuration in progress - Step 29)

## Project Structure

```
temporal-marathon-trivia/
├── config/
│   ├── event.toml              # Event configuration
│   └── questions.json          # Trivia questions
├── src/
│   ├── workflows/              # Temporal workflows
│   │   ├── event.py           # EventWorkflow (parent)
│   │   ├── daily.py           # DailyWorkflow (child)
│   │   └── player.py          # PlayerEntityWorkflow (child)
│   ├── activities/             # Temporal activities
│   │   ├── config.py          # Load TOML configuration
│   │   ├── questions.py       # Load and validate questions
│   │   ├── email.py           # Email validation
│   │   ├── export.py          # S3 CSV export
│   │   └── time.py            # Timezone conversions
│   ├── models/                 # Data models
│   │   ├── question.py        # Question model
│   │   ├── player.py          # Player model
│   │   ├── config.py          # EventConfig model
│   │   ├── ux_config.py       # UXConfig model
│   │   ├── state.py           # Workflow state models
│   │   ├── answer.py          # Request/response models
│   │   └── leaderboard.py     # LeaderboardEntry model
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # App initialization
│   │   └── routes/            # API endpoints
│   │       ├── player.py      # Registration
│   │       ├── gameplay.py    # Question/answer flow
│   │       └── leaderboard.py # Leaderboard queries
│   ├── worker.py               # Temporal worker entry point
│   └── temporal_client.py      # Connection utility
├── frontend/
│   ├── templates/              # Jinja2 templates
│   │   ├── base.html          # Base layout
│   │   ├── landing.html       # Landing page
│   │   └── components/        # Reusable components
│   └── static/                 # Static assets (future)
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test fixtures
├── scripts/
│   └── start_event.py          # Event initialization
├── Justfile                    # Task runner commands
├── pyproject.toml              # Python dependencies
└── README.md                   # This file
```

## Contributing

This is a reference implementation for Temporal's entity workflow pattern. Key design decisions:

- **TDD Approach**: Write tests first, implement to pass, refactor
- **Type Safety**: mypy --strict mode, no `Any` types
- **Simple Solutions**: No over-engineering, match existing patterns
- **Testing Focus**: 80%+ coverage on application logic only

See `CLAUDE.md` for detailed development guidelines.

## Documentation

- **spec.md**: Complete technical specification (13,000+ words)
- **plan.md**: 35-step TDD implementation plan
- **todo.md**: Progress tracking
- **CLAUDE.md**: Development guidelines and patterns

## License

Copyright © 2025 Temporal Technologies Inc.

This is a reference implementation for educational purposes.

## Support

- **Temporal Slack**: [temporalio.slack.com](https://temporalio.slack.com)
- **Temporal Docs**: [docs.temporal.io](https://docs.temporal.io)
- **Issues**: File via GitHub (when repository is public)

---

**Current Status**: Phase 5 (Frontend) - 71.4% complete (25/35 steps)

Ready for demo with <2000 concurrent players. 🎮
