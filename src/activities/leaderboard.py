# ABOUTME: Leaderboard-related activities for cross-workflow communication.
# Handles submitting player scores to DailyWorkflow from PlayerEntityWorkflow.

import asyncio

from temporalio import activity

from src.models.answer import SubmitScoreRequest
from src.temporal_client import create_temporal_client
from src.workflows.daily import DailyWorkflow


class LeaderboardActivities:
    """Activity class for leaderboard-related operations."""

    @activity.defn
    def submit_score_to_daily_workflow(
        self, daily_workflow_id: str, request: SubmitScoreRequest
    ) -> None:
        """Submit a player's score to the DailyWorkflow for leaderboard aggregation.

        This activity allows PlayerEntityWorkflow to communicate with DailyWorkflow
        by calling the DailyWorkflow's submit_score update handler.

        Note: This is a synchronous activity that wraps async Temporal client calls
        using asyncio.run(). This is necessary for compatibility with ThreadPoolExecutor
        in the worker and test fixtures.

        Args:
            daily_workflow_id: The workflow ID of the DailyWorkflow (e.g., "marathon-trivia-event-day-2025-11-26")
            request: SubmitScoreRequest containing player_id, score, email, first_name, last_name

        Raises:
            Exception: If the DailyWorkflow cannot be reached or the update fails
        """
        activity.logger.info(
            f"Submitting score for player {request.player_id} to DailyWorkflow {daily_workflow_id}"
        )

        # Define async inner function
        async def _submit_score() -> None:
            # Create Temporal client
            client = await create_temporal_client()

            # Get handle to DailyWorkflow
            daily_handle = client.get_workflow_handle(daily_workflow_id)

            # Call submit_score update handler on DailyWorkflow
            await daily_handle.execute_update(
                DailyWorkflow.submit_score,
                request,
            )

        # Run async code in sync context
        asyncio.run(_submit_score())

        activity.logger.info(
            f"Successfully submitted score {request.score} for player {request.player_id}"
        )
