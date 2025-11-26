# ABOUTME: Leaderboard API routes.
# Provides leaderboard display and player search functionality.

import json
import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from temporalio.client import Client

from src.models.answer import EventStatusResponse
from src.models.leaderboard import LeaderboardEntry
from src.workflows.daily import DailyWorkflow
from src.workflows.event import EventWorkflow

router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


@router.get("/api/leaderboard", response_class=HTMLResponse)
async def get_leaderboard(request: Request) -> HTMLResponse:
    """Get aggregated leaderboard across all event days.

    This endpoint:
    1. Checks Redis cache for leaderboard data (30s TTL)
    2. If cache miss, queries EventWorkflow for daily_workflow_ids
    3. Queries each DailyWorkflow for its leaderboard
    4. Aggregates player scores across all days
    5. Calculates final rankings with tie handling
    6. Caches result and returns HTML fragment

    Returns:
        HTMLResponse: HTML table fragment with leaderboard data

    Raises:
        HTTPException: If EventWorkflow cannot be found or queried
    """
    redis = request.app.state.redis
    temporal_client: Client = request.app.state.temporal_client

    # Check cache first (30s TTL)
    cached_data = await redis.get("leaderboard:full")
    if cached_data:
        # Cache hit - deserialize and render
        leaderboard_entries = [LeaderboardEntry(**entry) for entry in json.loads(cached_data)]
        # Get event dates from first entry (if any)
        event_dates = []
        if leaderboard_entries:
            event_dates = sorted(leaderboard_entries[0].daily_scores.keys())

        return templates.TemplateResponse(
            request,
            "components/leaderboard.html",
            {
                "leaderboard": leaderboard_entries,
                "event_dates": event_dates,
            },
        )

    # Cache miss - query Temporal workflows
    event_workflow_id = os.getenv("EVENT_WORKFLOW_ID", "marathon-trivia-event")
    event_handle = temporal_client.get_workflow_handle(event_workflow_id)

    # Get daily workflow IDs
    event_status: EventStatusResponse = await event_handle.query(EventWorkflow.get_event_status)
    daily_workflow_ids: dict[str, str] = event_status.daily_workflow_ids

    # Query each DailyWorkflow for its leaderboard
    # Structure: list of (date, leaderboard) tuples
    all_daily_leaderboards: list[tuple[str, list[LeaderboardEntry]]] = []
    for date_str, workflow_id in sorted(daily_workflow_ids.items()):
        daily_handle = temporal_client.get_workflow_handle(workflow_id)
        daily_leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)
        all_daily_leaderboards.append((date_str, daily_leaderboard))

    # Aggregate leaderboards
    aggregated_leaderboard = aggregate_leaderboards(all_daily_leaderboards)

    # Get event dates (sorted)
    event_dates = sorted(daily_workflow_ids.keys())

    # Cache aggregated data (30s TTL)
    # Serialize to JSON for caching
    cache_data = json.dumps(
        [
            {
                "rank": entry.rank,
                "display_name": entry.display_name,
                "total_score": entry.total_score,
                "daily_scores": entry.daily_scores,
                "email": entry.email,
            }
            for entry in aggregated_leaderboard
        ]
    )
    await redis.set("leaderboard:full", cache_data, ex=30)

    # Render template
    return templates.TemplateResponse(
        request,
        "components/leaderboard.html",
        {
            "leaderboard": aggregated_leaderboard,
            "event_dates": event_dates,
        },
    )


def aggregate_leaderboards(
    daily_leaderboards: list[tuple[str, list[LeaderboardEntry]]],
) -> list[LeaderboardEntry]:
    """Aggregate player scores across multiple daily leaderboards.

    This function:
    1. Collects all players from all daily leaderboards
    2. Merges daily scores for each player (by email)
    3. Calculates total scores (sum of all daily scores)
    4. Sorts by total_score descending, then alphabetically by display_name
    5. Assigns ranks with tie handling (tied players share rank, next rank adjusts)

    Args:
        daily_leaderboards: List of (date, leaderboard) tuples from each DailyWorkflow

    Returns:
        List of aggregated LeaderboardEntry objects, sorted by rank

    Example:
        >>> day1 = [LeaderboardEntry(1, "Alice B.", 50, {}, "alice@example.com")]
        >>> day2 = [LeaderboardEntry(1, "Alice B.", 60, {}, "alice@example.com")]
        >>> result = aggregate_leaderboards([("2025-03-10", day1), ("2025-03-11", day2)])
        >>> result[0].total_score
        110
        >>> result[0].daily_scores
        {"2025-03-10": 50, "2025-03-11": 60}
    """
    # Aggregate players by email
    player_data: dict[str, dict[str, Any]] = {}

    for date_str, daily_leaderboard in daily_leaderboards:
        for entry in daily_leaderboard:
            if entry.email not in player_data:
                # First time seeing this player
                player_data[entry.email] = {
                    "display_name": entry.display_name,
                    "email": entry.email,
                    "daily_scores": {},
                }

            # Map total_score from DailyWorkflow to the correct date in daily_scores
            # DailyWorkflow returns total_score for that day but daily_scores is empty
            player_data[entry.email]["daily_scores"][date_str] = entry.total_score

    # Calculate total scores and create entries
    aggregated_entries = []
    for email, data in player_data.items():
        total_score = sum(data["daily_scores"].values())
        aggregated_entries.append(
            LeaderboardEntry(
                rank=0,  # Will be assigned after sorting
                display_name=data["display_name"],
                total_score=total_score,
                daily_scores=data["daily_scores"],
                email=email,
            )
        )

    # Sort by total_score descending, then alphabetically by display_name
    aggregated_entries.sort(key=lambda entry: (-entry.total_score, entry.display_name))

    # Assign ranks with tie handling
    current_rank = 1
    for i, entry in enumerate(aggregated_entries):
        if i > 0 and entry.total_score < aggregated_entries[i - 1].total_score:
            # Score changed - adjust rank
            current_rank = i + 1

        # Assign rank (tied players get same rank)
        aggregated_entries[i] = LeaderboardEntry(
            rank=current_rank,
            display_name=entry.display_name,
            total_score=entry.total_score,
            daily_scores=entry.daily_scores,
            email=entry.email,
        )

    return aggregated_entries


@router.get("/api/config")
async def get_config(request: Request) -> dict[str, Any]:
    """Get event configuration for frontend initialization.

    This endpoint returns combined EventConfig and UXConfig data as JSON.
    Configuration is loaded once at API startup and cached permanently in Redis.

    Returns:
        dict: Combined configuration with event details, dates, and UX settings

    Response Schema:
        {
            "title": str,
            "description": str,
            "start_date": str (ISO format),
            "end_date": str (ISO format),
            "day_start_time": str (HH:MM:SS),
            "day_end_time": str (HH:MM:SS),
            "dates": list[str] (all event dates),
            "colors": {
                "primary": str,
                "secondary": str,
                "background": str,
                "text": str
            }
        }
    """
    redis = request.app.state.redis
    config = request.app.state.config
    ux_config = request.app.state.ux_config

    # Check Redis cache (permanent - no expiration)
    cache_key = "config:event"
    cached_json = await redis.get(cache_key)
    if cached_json:
        result: dict[str, Any] = json.loads(cached_json)
        return result

    # Cache miss - build response from app.state
    all_dates = config.get_all_dates()
    response_data = {
        "title": ux_config.title,
        "description": ux_config.description,
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "day_start_time": config.day_start_time.isoformat(),
        "day_end_time": config.day_end_time.isoformat(),
        "dates": [d.isoformat() for d in all_dates],
        "colors": {
            "primary": ux_config.primary_color,
            "secondary": ux_config.secondary_color,
            "background": ux_config.background_color,
            "text": ux_config.text_color,
        },
    }

    # Cache permanently (no expiration)
    await redis.set(cache_key, json.dumps(response_data))

    return response_data
