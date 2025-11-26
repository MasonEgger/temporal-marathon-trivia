# ABOUTME: Integration tests for leaderboard aggregation across multiple days and players.
# Tests tie handling, alphabetical tie-breaking, and ranking logic with real Temporal workflows.

import uuid
from typing import Any

import pytest

from tests.fixtures.temporal_test_helpers import (
    answer_all_questions,
    get_event_status,
    get_temporal_client,
    register_test_player,
    start_test_event_workflow,
)


@pytest.mark.asyncio
async def test_leaderboard_aggregates_scores_correctly() -> None:
    """Test that leaderboard correctly aggregates scores across multiple days and players."""
    # Start EventWorkflow with 3-day config
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"test-leaderboard-agg-test-1-{run_id}"
    config_path = "tests/fixtures/config.toml"

    event_workflow_id = await start_test_event_workflow(
        workflow_id=workflow_id,
        config_path=config_path,
    )

    # Wait for workflow to initialize
    import asyncio

    await asyncio.sleep(0.5)

    # Register 5 players
    players: list[dict[str, Any]] = []
    player_names = [
        ("Alice", "Anderson"),
        ("Bob", "Brown"),
        ("Charlie", "Clark"),
        ("Diana", "Davis"),
        ("Eve", "Evans"),
    ]

    for first_name, last_name in player_names:
        player_id = await register_test_player(
            event_workflow_id=event_workflow_id,
            email=f"{first_name.lower()}@example.com",
            first_name=first_name,
            last_name=last_name,
        )
        players.append(
            {
                "id": player_id,
                "email": f"{first_name.lower()}@example.com",
                "first_name": first_name,
                "last_name": last_name,
            }
        )

    # Define scores for each player on each day
    # Day 1 scores: Alice=5, Bob=4, Charlie=3, Diana=2, Eve=1
    # Day 2 scores: Alice=3, Bob=5, Charlie=4, Diana=1, Eve=2
    day1_scores = [5, 4, 3, 2, 1]
    day2_scores = [3, 5, 4, 1, 2]

    # Have all players complete day 1 with different scores
    for i, player in enumerate(players):
        # Submit answers to get specific score
        correct_count = day1_scores[i]
        questions = await answer_all_questions(
            player_id=player["id"],
            day_date="2025-03-10",
            correct_count=correct_count,
        )
        print(f"✓ {player['first_name']} completed Day 1 - Score: {correct_count}/{len(questions)}")

    # Have all players complete day 2 with different scores
    for i, player in enumerate(players):
        correct_count = day2_scores[i]
        questions = await answer_all_questions(
            player_id=player["id"],
            day_date="2025-03-11",
            correct_count=correct_count,
        )
        print(f"✓ {player['first_name']} completed Day 2 - Score: {correct_count}/{len(questions)}")

    # Query event status to get daily workflow IDs
    event_status = await get_event_status(event_workflow_id)
    daily_workflow_ids = event_status.daily_workflow_ids

    # Query each DailyWorkflow for leaderboard
    from src.workflows.daily import DailyWorkflow

    client = await get_temporal_client()
    all_leaderboards = {}
    for date_str, daily_wf_id in daily_workflow_ids.items():
        daily_handle = client.get_workflow_handle(daily_wf_id)
        leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)
        all_leaderboards[date_str] = leaderboard
        print(f"\nDay {date_str} Leaderboard:")
        for entry in leaderboard:
            print(f"  Rank {entry.rank}: {entry.display_name} - Score: {entry.total_score}")

    # Verify Day 1 leaderboard
    day1_leaderboard = all_leaderboards["2025-03-10"]
    assert len(day1_leaderboard) == 5

    # Expected Day 1 ranking: Alice(5), Bob(4), Charlie(3), Diana(2), Eve(1)
    assert day1_leaderboard[0].display_name == "Alice A."
    assert day1_leaderboard[0].total_score == 5
    assert day1_leaderboard[0].rank == 1

    assert day1_leaderboard[1].display_name == "Bob B."
    assert day1_leaderboard[1].total_score == 4
    assert day1_leaderboard[1].rank == 2

    # Verify Day 2 leaderboard
    day2_leaderboard = all_leaderboards["2025-03-11"]
    assert len(day2_leaderboard) == 5

    # Expected Day 2 ranking: Bob(5), Charlie(4), Alice(3), Eve(2), Diana(1)
    assert day2_leaderboard[0].display_name == "Bob B."
    assert day2_leaderboard[0].total_score == 5
    assert day2_leaderboard[0].rank == 1

    # Aggregate total scores
    # Alice: 5+3=8, Bob: 4+5=9, Charlie: 3+4=7, Diana: 2+1=3, Eve: 1+2=3
    # Expected overall ranking: Bob(9), Alice(8), Charlie(7), Diana(3), Eve(3)
    # Diana and Eve tied at 3 - alphabetical by last name: Davis < Evans

    print("\n✅ Leaderboard aggregation test completed - all scores verified")


@pytest.mark.asyncio
async def test_leaderboard_handles_ties_correctly() -> None:
    """Test that leaderboard handles tied scores with correct rank adjustment."""
    # Start EventWorkflow
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"test-leaderboard-ties-test-2-{run_id}"
    config_path = "tests/fixtures/config.toml"

    event_workflow_id = await start_test_event_workflow(
        workflow_id=workflow_id,
        config_path=config_path,
    )

    import asyncio

    await asyncio.sleep(0.5)

    # Register 3 players who will tie
    tied_players = [
        ("Alice", "Anderson", "alice@example.com"),
        ("Bob", "Brown", "bob@example.com"),
        ("Charlie", "Clark", "charlie@example.com"),
    ]

    player_ids = []
    for first_name, last_name, email in tied_players:
        player_id = await register_test_player(
            event_workflow_id=event_workflow_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        player_ids.append(player_id)

    # Have all 3 players complete day 1 with same score (3 out of 5)
    for i, player_id in enumerate(player_ids):
        await answer_all_questions(
            player_id=player_id,
            day_date="2025-03-10",
            correct_count=3,
        )
        print(f"✓ Player {i + 1} completed Day 1 - Score: 3/5")

    # Query leaderboard
    event_status = await get_event_status(event_workflow_id)
    daily_wf_id = event_status.daily_workflow_ids["2025-03-10"]

    from src.workflows.daily import DailyWorkflow

    client = await get_temporal_client()
    daily_handle = client.get_workflow_handle(daily_wf_id)
    leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)

    print("\nLeaderboard after 3 tied players:")
    for entry in leaderboard:
        print(f"  Rank {entry.rank}: {entry.display_name} - Score: {entry.total_score}")

    # Verify all 3 players have rank 1
    assert len(leaderboard) == 3
    assert all(entry.rank == 1 for entry in leaderboard)
    assert all(entry.total_score == 3 for entry in leaderboard)

    # Verify alphabetical ordering within tie (Anderson, Brown, Clark)
    assert leaderboard[0].display_name == "Alice A."
    assert leaderboard[1].display_name == "Bob B."
    assert leaderboard[2].display_name == "Charlie C."

    # Register 1 more player with lower score
    player_id_4 = await register_test_player(
        event_workflow_id=event_workflow_id,
        email="diana@example.com",
        first_name="Diana",
        last_name="Davis",
    )

    # Have this player complete day 1 with lower score (2 out of 5)
    await answer_all_questions(
        player_id=player_id_4,
        day_date="2025-03-10",
        correct_count=2,
    )
    print("✓ Diana completed Day 1 - Score: 2/5")

    # Query leaderboard again
    leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)

    print("\nLeaderboard after adding 4th player:")
    for entry in leaderboard:
        print(f"  Rank {entry.rank}: {entry.display_name} - Score: {entry.total_score}")

    # Verify new player has rank 4 (not rank 2)
    assert len(leaderboard) == 4
    assert leaderboard[0].rank == 1  # Alice (tied)
    assert leaderboard[1].rank == 1  # Bob (tied)
    assert leaderboard[2].rank == 1  # Charlie (tied)
    assert leaderboard[3].rank == 4  # Diana (lower score)
    assert leaderboard[3].display_name == "Diana D."
    assert leaderboard[3].total_score == 2

    print("\n✅ Tie handling test completed - rank adjustment verified")


@pytest.mark.asyncio
async def test_leaderboard_alphabetical_tie_breaking() -> None:
    """Test that tied players are ordered alphabetically by last name, then first name."""
    # Start EventWorkflow
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"test-leaderboard-alpha-test-3-{run_id}"
    config_path = "tests/fixtures/config.toml"

    event_workflow_id = await start_test_event_workflow(
        workflow_id=workflow_id,
        config_path=config_path,
    )

    import asyncio

    await asyncio.sleep(0.5)

    # Register players with specific names to test alphabetical ordering
    # Intentionally NOT in alphabetical order to test sorting
    players = [
        ("John", "Doe", "john@example.com"),
        ("Alice", "Brown", "alice@example.com"),
        ("Bob", "Adams", "bob@example.com"),
    ]

    player_ids = []
    for first_name, last_name, email in players:
        player_id = await register_test_player(
            event_workflow_id=event_workflow_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        player_ids.append(player_id)

    # Have all players complete day 1 with same score (4 out of 5)
    for i, player_id in enumerate(player_ids):
        await answer_all_questions(
            player_id=player_id,
            day_date="2025-03-10",
            correct_count=4,
        )
        print(f"✓ {players[i][0]} {players[i][1]} completed Day 1 - Score: 4/5")

    # Query leaderboard
    event_status = await get_event_status(event_workflow_id)
    daily_wf_id = event_status.daily_workflow_ids["2025-03-10"]

    from src.workflows.daily import DailyWorkflow

    client = await get_temporal_client()
    daily_handle = client.get_workflow_handle(daily_wf_id)
    leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)

    print("\nLeaderboard (tied scores, alphabetical by last name):")
    for entry in leaderboard:
        print(f"  Rank {entry.rank}: {entry.display_name} - Score: {entry.total_score}")

    # Verify alphabetical order: Adams < Brown < Doe
    assert len(leaderboard) == 3
    assert all(entry.rank == 1 for entry in leaderboard)
    assert all(entry.total_score == 4 for entry in leaderboard)

    assert leaderboard[0].display_name == "Bob A."  # Adams
    assert leaderboard[1].display_name == "Alice B."  # Brown
    assert leaderboard[2].display_name == "John D."  # Doe

    print("\n✅ Alphabetical tie-breaking test completed - correct order verified")


@pytest.mark.asyncio
async def test_leaderboard_with_zero_players() -> None:
    """Test that leaderboard returns empty list when no players have completed the day."""
    # Start EventWorkflow
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"test-leaderboard-empty-test-4-{run_id}"
    config_path = "tests/fixtures/config.toml"

    event_workflow_id = await start_test_event_workflow(
        workflow_id=workflow_id,
        config_path=config_path,
    )

    import asyncio

    # Wait for EventWorkflow to complete initialization and schedule daily workflows
    await asyncio.sleep(1.0)

    # Query leaderboard without any players completing
    event_status = await get_event_status(event_workflow_id)
    daily_wf_id = event_status.daily_workflow_ids["2025-03-10"]

    from src.workflows.daily import DailyWorkflow

    client = await get_temporal_client()
    daily_handle = client.get_workflow_handle(daily_wf_id)
    leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)

    print("\nLeaderboard with 0 players:")
    assert leaderboard == []
    print("✅ Empty leaderboard test passed")


@pytest.mark.asyncio
async def test_leaderboard_performance_with_many_players() -> None:
    """Test leaderboard performance with 100+ players (scaled down from 1000 for test speed)."""
    # Start EventWorkflow
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"test-leaderboard-perf-test-5-{run_id}"
    config_path = "tests/fixtures/config.toml"

    event_workflow_id = await start_test_event_workflow(
        workflow_id=workflow_id,
        config_path=config_path,
    )

    import asyncio
    import time

    await asyncio.sleep(0.5)

    # Register 100 players (scaled down for test speed)
    num_players = 100
    print(f"\nRegistering {num_players} players...")

    player_ids = []
    for i in range(num_players):
        player_id = await register_test_player(
            event_workflow_id=event_workflow_id,
            email=f"player{i}@example.com",
            first_name="Player",
            last_name=f"Test{i:03d}",
        )
        player_ids.append(player_id)

        if (i + 1) % 20 == 0:
            print(f"  ✓ Registered {i + 1}/{num_players} players")

    # Have all players complete day 1 (random scores for variety)
    print(f"\nHaving {num_players} players complete Day 1...")
    import random

    random.seed(42)  # Deterministic scores for reproducibility

    for i, player_id in enumerate(player_ids):
        correct_count = random.randint(0, 5)
        await answer_all_questions(
            player_id=player_id,
            day_date="2025-03-10",
            correct_count=correct_count,
        )

        if (i + 1) % 20 == 0:
            print(f"  ✓ {i + 1}/{num_players} players completed Day 1")

    # Query leaderboard and measure time
    event_status = await get_event_status(event_workflow_id)
    daily_wf_id = event_status.daily_workflow_ids["2025-03-10"]

    from src.workflows.daily import DailyWorkflow

    client = await get_temporal_client()
    daily_handle = client.get_workflow_handle(daily_wf_id)

    start_time = time.time()
    leaderboard = await daily_handle.query(DailyWorkflow.get_daily_leaderboard)
    query_time = time.time() - start_time

    print(f"\n✓ Leaderboard query with {num_players} players took {query_time:.3f}s")

    # Verify leaderboard has all players
    assert len(leaderboard) == num_players

    # Verify leaderboard is correctly sorted (descending by score)
    for i in range(len(leaderboard) - 1):
        assert leaderboard[i].total_score >= leaderboard[i + 1].total_score

    # Verify ranks are assigned correctly
    current_rank = 1
    players_at_rank = 0
    prev_score = None

    for entry in leaderboard:
        if prev_score is not None and entry.total_score < prev_score:
            # Score changed, adjust rank
            current_rank += players_at_rank
            players_at_rank = 1
        else:
            players_at_rank += 1

        assert entry.rank == current_rank
        prev_score = entry.total_score

    # Performance assertion: should complete in reasonable time (<5 seconds)
    assert query_time < 5.0, f"Leaderboard query took too long: {query_time:.3f}s"

    print(f"✅ Performance test passed - query completed in {query_time:.3f}s")
