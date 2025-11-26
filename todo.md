# Marathon Trivia Platform - Implementation Todo

**Last Updated**: 2025-11-25

This file tracks the implementation progress of the Marathon Trivia Platform. Each checkbox corresponds to a numbered step in plan.md.

---

## Phase 1: Project Foundation

### Step 1: Project Structure and Dependencies
- [x] Create project directory structure (src/, tests/, config/, frontend/, docs/)
- [x] Create pyproject.toml with dependencies and dev tools
- [x] Create Justfile with initial tasks (test, lint, format, typecheck, check)
- [x] Create .gitignore with Python ignores
- [x] Create .env.example with environment variables
- [x] Initialize uv lock file (run uv sync)
- [x] Verify setup (run just check)

### Step 2: Core Data Models - Question
- [x] Write Question model tests (valid data, options validation, correct_answer validation)
- [x] Implement Question dataclass with pydantic validation
- [x] Add validators for A/B/C/D format and correct_answer
- [x] Refactor validation error messages
- [x] Verify tests pass and run just check

### Step 3: Core Data Models - Player
- [x] Write Player model tests (creation, display_name, email validation)
- [x] Implement Player dataclass with fields and defaults
- [x] Add get_display_name() method with "FirstName L." format
- [x] Refactor with helper methods if needed
- [x] Verify tests pass and run just check

### Step 4: Core Data Models - LeaderboardEntry and EventConfig
- [x] Write LeaderboardEntry tests
- [x] Implement LeaderboardEntry dataclass
- [x] Write EventConfig tests (date validation, timezone validation, questions_per_day)
- [x] Implement EventConfig dataclass with workflow-essential fields only
- [x] Add validators for dates, timezone, questions_per_day
- [x] Add get_all_dates() helper method to EventConfig
- [x] Verify tests pass and run just check

---

## Phase 2: Configuration and Question Loading

### Step 5: TOML Configuration Loading Activity
- [x] Write configuration activity tests (valid TOML, missing file, malformed TOML)
- [x] Create test fixture config.toml (3-day event, 5 questions per day)
- [x] Implement load_event_config() activity with TOML parsing
- [x] Add error handling for missing files and malformed TOML
- [x] Refactor error messages for clarity
- [x] Verify tests pass and run just check

### Step 6: Questions JSON Loading Activity
- [x] Write questions activity tests (valid JSON, validation, missing file)
- [x] Create test fixture questions.json (3 days, 5 questions per day)
- [x] Implement load_questions() activity
- [x] Implement get_questions_for_day() activity
- [x] Write validate_questions_file() tests
- [x] Implement validate_questions_file() activity
- [x] Refactor with caching if needed
- [x] Verify tests pass and run just check

### Step 7: Email Validation Activity
- [x] Write email validation tests (valid email, consumer domains, invalid format)
- [x] Implement validate_email() activity with regex and domain blocking
- [x] Refactor domain validation (case-insensitive)
- [x] Verify tests pass and run just check

### Step 8: S3 CSV Export Activity
- [x] Write CSV export tests (format, columns, S3 upload, empty list)
- [x] Create test fixtures for players (create_test_player, create_test_players)
- [x] Implement export_daily_csv_to_s3() activity
- [x] Write integration test with moto for S3
- [x] Make integration test pass
- [x] Refactor with retry logic and error handling
- [x] Verify tests pass and run just check

---

## Phase 3: Workflow Implementation - Player Entity

### Step 9: PlayerEntityWorkflow - Basic Structure
- [x] Write PlayerEntityWorkflow initialization tests
- [x] Create temporal test environment fixture (using pydantic_data_converter)
- [x] Implement PlayerEntityWorkflow with basic structure
- [x] Add workflow.run method with player initialization
- [x] Add workflow.query methods (get_current_state, get_score_for_day, has_completed_day)
- [x] Refactor with proper type hints
- [x] Verify tests pass and run just check

### Step 10: PlayerEntityWorkflow - Start Day Update Handler
- [x] Write start_day update handler tests
- [x] Implement start_day update handler
- [x] Configure activity execution with timeouts
- [x] Mock activity in tests
- [x] Refactor with validation
- [x] Verify tests pass and run just check

### Step 11: PlayerEntityWorkflow - Submit Answer Update Handler
- [x] Write submit_answer update handler tests (correct/incorrect, next question, completion, validation)
- [x] Define AnswerResult dataclass (in src/models/answer.py)
- [x] Define SubmitAnswerRequest dataclass (for type safety)
- [x] Implement submit_answer update handler (using ApplicationError for failures)
- [x] Refactor with helper methods (_get_current_question, _is_answer_correct)
- [x] Verify tests pass and run just check

### Step 12: DailyWorkflow - Basic Structure
- [x] Write DailyWorkflow initialization tests
- [x] Implement DailyWorkflow with basic structure
- [x] Add workflow.run method with daily state initialization
- [x] Add workflow.query methods (get_daily_leaderboard, is_day_active)
- [x] Refactor with timezone support
- [x] Verify tests pass and run just check

### Step 13: DailyWorkflow - Leaderboard Ranking Logic
- [x] Write leaderboard ranking tests (sorting, ties, alphabetical tie-breaking)
- [x] Create calculate_leaderboard() helper function
- [x] Implement get_daily_leaderboard() query
- [x] Write submit_score update handler tests
- [x] Implement submit_score update handler
- [x] Make submit_score tests pass
- [x] Refactor ranking logic if needed
- [x] Verify tests pass and run just check

### Step 14: EventWorkflow - Basic Structure
- [x] Write EventWorkflow initialization tests
- [x] Implement EventWorkflow with basic structure
- [x] Add workflow.run method with config loading
- [x] Add workflow.query method (get_event_status)
- [x] Refactor with error handling for config loading
- [x] Verify tests pass and run just check

### Step 15: EventWorkflow - Player Registration
- [ ] Write register_player update handler tests (new player, duplicate, validation)
- [ ] Implement register_player update handler
- [ ] Add child workflow creation for PlayerEntityWorkflow
- [ ] Refactor with player lookup helper
- [ ] Verify tests pass and run just check

### Step 16: EventWorkflow - Daily Workflow Scheduling
- [ ] Write daily workflow scheduling tests
- [ ] Implement daily workflow scheduling in run() method
- [ ] Add timer-based workflow starting
- [ ] Refactor with _schedule_daily_workflow helper
- [ ] Verify tests pass and run just check

---

## Phase 4: API Layer Implementation

### Step 17: FastAPI Application Setup
- [ ] Write API setup tests (app creation, health endpoint, Temporal client)
- [ ] Implement FastAPI app with main.py
- [ ] Create RedisCache utility class
- [ ] Add lifespan context manager for connections
- [ ] Write cache tests with fakeredis
- [ ] Make cache tests pass
- [ ] Refactor with configuration management
- [ ] Verify tests pass and run just check

### Step 18: API Routes - Player Registration
- [ ] Write player registration endpoint tests
- [ ] Implement POST /api/join endpoint
- [ ] Create HTML templates (join-success.html, error.html)
- [ ] Update main.py to include player router
- [ ] Refactor with template rendering utility
- [ ] Verify tests pass and run just check

### Step 19: API Routes - Gameplay Start Day
- [ ] Write start day endpoint tests
- [ ] Implement GET /api/day/{date}/start endpoint
- [ ] Create question.html template
- [ ] Update main.py to include gameplay router
- [ ] Refactor with validation helpers
- [ ] Verify tests pass and run just check

### Step 20: API Routes - Submit Answer
- [ ] Write submit answer endpoint tests
- [ ] Implement POST /api/day/{date}/answer endpoint
- [ ] Create completion.html and answer-feedback.html templates
- [ ] Add score submission to DailyWorkflow
- [ ] Refactor with error handling
- [ ] Verify tests pass and run just check

### Step 21: API Routes - Leaderboard
- [ ] Write leaderboard endpoint tests with Redis caching
- [ ] Implement GET /api/leaderboard endpoint
- [ ] Create leaderboard.html template
- [ ] Update main.py to include leaderboard router
- [ ] Refactor with aggregation helper function
- [ ] Verify tests pass and run just check

### Step 22: API Routes - Configuration and Player Lookup
- [ ] Write config and player endpoints tests
- [ ] Implement GET /api/config endpoint with caching
- [ ] Implement GET /api/player endpoint with highlighting
- [ ] Update templates for player highlighting
- [ ] Refactor with player state caching
- [ ] Verify tests pass and run just check

---

## Phase 5: Frontend and Integration

### Step 23: Frontend Templates - Landing Page
- [ ] Create base.html template with Tailwind and HTMX
- [ ] Create landing.html template (join form and returning player view)
- [ ] Create day-button.html component
- [ ] Add GET / landing page route to main.py
- [ ] Write landing page rendering tests
- [ ] Verify templates render correctly

### Step 24: Frontend Styling with Tailwind
- [ ] Update base.html with Tailwind configuration and custom colors
- [ ] Style landing.html (form, day buttons, leaderboard container)
- [ ] Style question.html (card layout, radio buttons)
- [ ] Style leaderboard.html (table, striped rows, top 3 highlighting)
- [ ] Style completion.html and error.html
- [ ] Create custom CSS if needed (frontend/static/css/styles.css)
- [ ] Test responsive design at different breakpoints
- [ ] Verify high contrast and readability

### Step 25: Worker and Temporal Client Setup
- [ ] Implement src/worker.py with workflow and activity registration
- [ ] Create src/temporal_client.py with connection utility
- [ ] Write worker tests (creation, TLS configuration)
- [ ] Make worker tests pass
- [ ] Update API to use connection utility
- [ ] Verify worker starts successfully
- [ ] Verify tests pass and run just check

### Step 26: Integration Test - Full Player Journey
- [ ] Write full player journey integration test
- [ ] Test player registration, answering questions, leaderboard
- [ ] Test multi-day gameplay
- [ ] Test duplicate email handling
- [ ] Make integration tests pass
- [ ] Refactor with test helpers
- [ ] Verify integration tests pass with just test-integration

### Step 27: Integration Test - Leaderboard Aggregation
- [ ] Write leaderboard aggregation integration test (multiple players and days)
- [ ] Test tie handling and ranking
- [ ] Test alphabetical tie-breaking
- [ ] Make leaderboard integration tests pass
- [ ] Refactor with edge case tests
- [ ] Verify integration tests pass with just test-integration

---

## Phase 6: Deployment and Documentation

### Step 28: Docker Configuration
- [ ] Create Dockerfile with multi-stage build
- [ ] Create docker-compose.yml with all services
- [ ] Create .dockerignore
- [ ] Test Docker build
- [ ] Test Docker Compose startup
- [ ] Create docker-compose.dev.yml for development
- [ ] Document Docker usage in README.md

### Step 29: Justfile and Development Commands
- [ ] Create Justfile with all commands
- [ ] Add development commands (dev, worker, api)
- [ ] Add testing commands (test, test-unit, test-integration, coverage)
- [ ] Add linting commands (lint, format, typecheck, check)
- [ ] Add Docker commands (build, up, down, logs)
- [ ] Add data commands (export-csv, validate-config)
- [ ] Test all Justfile commands
- [ ] Document Justfile in README

### Step 30: Example Configuration Files
- [ ] Create config/event.example.toml with comprehensive documentation
- [ ] Create config/questions.example.json with sample questions
- [ ] Update .env.example with helpful comments
- [ ] Create scripts/validate_config.py validator script
- [ ] Test config validator on example and broken files
- [ ] Document configuration in docs/how-to/create-event.md

### Step 31: API Documentation
- [ ] Create docs/api/endpoints.md with all endpoint specifications
- [ ] Create docs/api/workflows.md with workflow documentation and diagrams
- [ ] Create docs/api/activities.md with activity documentation
- [ ] Create docs/api/data-models.md with dataclass documentation
- [ ] Enhance FastAPI OpenAPI docs with comprehensive docstrings
- [ ] Test all documentation examples

### Step 32: How-To Guides
- [ ] Create docs/how-to/setup.md with local development setup
- [ ] Create docs/how-to/deployment.md with Docker Compose and Temporal Cloud
- [ ] Create docs/how-to/create-event.md with event configuration guide
- [ ] Create docs/how-to/monitoring.md with monitoring and debugging guide
- [ ] Create docs/how-to/troubleshooting.md with common issues and solutions
- [ ] Test all guides step-by-step

### Step 33: README and Project Documentation
- [ ] Create README.md with overview, quick start, configuration, development
- [ ] Update CLAUDE.md with implementation learnings
- [ ] Create CONTRIBUTING.md with code style and PR process
- [ ] Create LICENSE file
- [ ] Verify all documentation links work

### Step 34: End-to-End Testing
- [ ] Write complete event lifecycle end-to-end test
- [ ] Test time-based day transitions
- [ ] Create performance test with 100+ concurrent players
- [ ] Make all end-to-end tests pass
- [ ] Verify integration tests pass with just test-integration

### Step 35: Final Testing and Quality Assurance
- [ ] Run full test suite (just test)
- [ ] Check test coverage >= 80% (just coverage)
- [ ] Run type checking (just typecheck)
- [ ] Run linting (just lint)
- [ ] Run formatting (just format)
- [ ] Run full check (just check)
- [ ] Manual testing with Docker Compose
- [ ] Load testing with 100+ players
- [ ] Security review (secrets, CORS, input validation, XSS)
- [ ] Documentation review (accuracy, links, examples)
- [ ] Verify all success criteria from spec
- [ ] Create release tag (v1.0.0)

---

## Overall Progress

**Phase 1: Project Foundation** - 4/4 steps complete (100%) ✅
**Phase 2: Configuration and Question Loading** - 4/4 steps complete (100%) ✅
**Phase 3: Workflow Implementation** - 6/8 steps complete (75.0%)
**Phase 4: API Layer** - 0/6 steps complete (0%)
**Phase 5: Frontend and Integration** - 0/5 steps complete (0%)
**Phase 6: Deployment and Documentation** - 0/8 steps complete (0%)

**Total Progress: 14/35 steps complete (40.0%)**

---

## Notes

- Update this file as each checkbox is completed
- Mark steps complete ONLY when all sub-tasks pass
- Each step should include: RED tests, GREEN implementation, REFACTOR improvements
- Run `just check` after each step before marking complete
- Update overall progress percentages regularly
