# ABOUTME: Player workflow verification utilities.
# Ensures PlayerEntityWorkflow exists for authenticated users, recreating if necessary.

import os
from typing import Any

from temporalio.client import Client, WorkflowHandle
from temporalio.service import RPCError


async def verify_player_workflow(player_id: str, temporal_client: Client) -> WorkflowHandle[Any, Any] | None:
    """Verify that a PlayerEntityWorkflow exists for the given player_id.

    This function handles the edge case where a user has a valid cookie but their
    workflow no longer exists (e.g., after Temporal server restart). It checks if
    the workflow exists, and if not, attempts to recreate it using EventWorkflow's
    player registry as the source of truth.

    Args:
        player_id: The workflow ID for the player's entity workflow
        temporal_client: Temporal client for querying workflows

    Returns:
        WorkflowHandle if workflow exists or was recreated, None if player not found in registry

    Flow:
        1. Try to get handle to PlayerEntityWorkflow
        2. If not found, query EventWorkflow registry
        3. If player in registry, return None (player should re-register to recreate workflow)
        4. If player not in registry, return None (invalid cookie)

    Note:
        Currently returns None if workflow doesn't exist. In the future, this could
        automatically recreate workflows, but for now we require re-registration.
    """
    try:
        # Try to get the PlayerEntityWorkflow handle
        player_handle = temporal_client.get_workflow_handle(player_id)

        # Verify workflow is actually running by describing it
        # This will raise RPCError if workflow doesn't exist
        await player_handle.describe()

        # Workflow exists and is running
        return player_handle

    except RPCError as e:
        # Workflow not found - check if player exists in EventWorkflow registry
        if "not found" in str(e).lower():
            # Player workflow doesn't exist
            # Check EventWorkflow registry to see if player was ever registered
            event_workflow_id = os.getenv("EVENT_WORKFLOW_ID", "marathon-trivia-event")

            try:
                temporal_client.get_workflow_handle(event_workflow_id)

                # Extract email from player_id (format: {event-id}-player-{initials}-{uuid})
                # For now, we can't easily get email from player_id, so just return None
                # User will need to re-register
                return None

            except RPCError:
                # EventWorkflow also doesn't exist - complete system reset
                return None
        else:
            # Some other RPC error - re-raise
            raise
