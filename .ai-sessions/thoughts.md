# Project Evolution: Sprint Trivia → Marathon Trivia Platform

**Date**: 2025-11-25

## Current State

I have a fully functional **"Sprint Trivia"** application (`temporal-trivia-python/`):
- **Model**: SMS/CLI-based, timed sessions (30 min), small groups (2-10 players)
- **Tech**: Python + Temporal workflows, LLM-generated questions, Update handlers
- **Status**: 100% complete, production-ready, 185 tests, 79% coverage
- **Frontend**: Existing Node.js/SvelteKit frontend (`temporal-trivia-frontend/`) built for SMS gameplay

## New Vision: Marathon Trivia Platform

I want to build a fundamentally different application - a **"Marathon Trivia Platform"**:

### Core Requirements
1. **Web-only interaction** (no SMS) - players join and play through browser
2. **All-day gameplay** - no time limits per question, game runs continuously
3. **Massive scale** - support 100s-1000s of concurrent players
4. **Asynchronous progression** - each player moves through questions at their own pace
5. **Live leaderboard** - running rankings updated in real-time
6. **Multi-day persistence** - scores aggregate across days
7. **Custom questions** - load from JSON file (no LLM generation needed)

### Why This is Different
- **Sprint**: Synchronous, everyone on same question, competitive timing, session-based
- **Marathon**: Asynchronous, self-paced, endurance-based, persistent platform

Think: **Wordle/daily trivia app** vs. **live quiz show**

## Architectural Changes Needed

### Backend (Temporal Workflows)
- **New workflow**: `MarathonTriviaWorkflow` - one per day with continue-as-new
- **Per-player state**: Track each player's current question, score, progress independently
- **Update handlers**: `join_game()`, `submit_answer()` for immediate feedback
- **Queries**: `get_leaderboard()`, `get_next_question()`, `get_player_progress()`
- **24-hour cycle**: Continue-as-new at midnight, aggregate scores across days
- **Question source**: JSON file activity (not LLM)

### Frontend (New SvelteKit App)
- **Landing page**: Join form + live leaderboard
- **Play page**: Display question, submit answer, immediate feedback, progress tracking
- **Leaderboard page**: Live rankings (today + all-time)
- **API layer**: Direct Temporal client or Express middleware
- **Real-time updates**: WebSocket or polling for leaderboard

## Decision: Fresh Implementation

**Why not port existing code?**
1. Old frontend is SMS-centric (Twilio webhooks, host/player model)
2. Old workflows assume synchronous, timed sessions
3. State management is session-based, not persistent
4. Polling patterns won't scale to 100s of players
5. Interaction model is fundamentally incompatible

**Approach:**
- Create new directory: `temporal-trivia-marathon/`
- Keep current implementation as reference (proven patterns)
- Reuse: tooling, testing setup, configs, Docker/K8s manifests
- Build fresh: workflows, activities, frontend, state management

## What I'm Keeping vs. Rebuilding

### Reuse from Current Implementation ✅
- Development tooling (Justfile, pyproject.toml, ruff/mypy configs)
- Testing infrastructure (pytest, Temporal test environment patterns)
- Configuration patterns (env vars, Temporal client setup)
- Base models (Question, Player dataclasses - adapted)
- Deployment manifests (Docker, K8s - renamed)
- Documentation structure (CLAUDE.md template)

### Build Fresh ❌
- Workflows (completely different state management)
- Activities (JSON loading vs. LLM generation)
- Frontend (web-based vs. SMS webhooks)
- CLI/UI (self-service vs. host-initiated)
- Leaderboard logic (live, scalable queries)
- Multi-day aggregation (continue-as-new strategy)

## Next Steps

1. **Create new directory**: `temporal-trivia-marathon/` with project scaffolding
2. **Design data model**: PlayerState, Question schema, Leaderboard structure
3. **Implement backend**: MarathonTriviaWorkflow with Update handlers
4. **Build prototype CLI**: Test join/answer/leaderboard flows
5. **Performance test**: Simulate 100+ concurrent players
6. **Build frontend**: SvelteKit app with play page + leaderboard
7. **Multi-day logic**: Continue-as-new + score aggregation

## Open Questions

- **Multi-day scores**: Workflow continuation vs. external DB vs. workflow search aggregation?
- **Scale target**: How many concurrent players? (impacts state size, query optimization)
- **Question management**: How many questions? Rotation strategy? Difficulty levels?
- **Leaderboard scope**: Top 100? Pagination? Player search?
- **Real-time updates**: WebSocket vs. polling? Update frequency?

## Lessons from Current Implementation

- **Update handlers work great** for immediate user feedback (CLI pattern)
- **Continue-as-new** requires explicit state passing, use positional args
- **Time-skipping tests** need `asyncio.sleep()` after signals for processing
- **Class-based activities** with Protocol DI enable clean testing
- **Defensive queries** return `.copy()` to prevent external mutation
- **State size matters** - consider scalability with 1000s of players

---

**Summary**: Building a new marathon trivia platform that shares Temporal patterns with the current sprint trivia app, but requires fresh architecture for persistent, asynchronous, massive-scale gameplay.
