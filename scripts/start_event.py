#!/usr/bin/env python3
# ABOUTME: Script to start the EventWorkflow for a Marathon Trivia event.
# Reads configuration from .env file and starts the workflow on a running Temporal server.

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.temporal_client import create_temporal_client
from src.workflows.event import EventWorkflow


async def main() -> None:
    """Start the EventWorkflow for the Marathon Trivia event."""
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("❌ Error: .env file not found. Please copy .env.example to .env")
        return

    load_dotenv(env_path)

    # Get configuration from environment
    workflow_id = os.getenv("EVENT_WORKFLOW_ID", "marathon-trivia-event")
    config_path = os.getenv("EVENT_CONFIG_PATH", "config/event.toml")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "marathon-trivia")

    # Verify config file exists
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"❌ Error: Config file not found at {config_path}")
        return

    print("=" * 80)
    print("Marathon Trivia Platform - Start Event Workflow")
    print("=" * 80)
    print(f"Workflow ID: {workflow_id}")
    print(f"Config Path: {config_path}")
    print(f"Task Queue: {task_queue}")
    print("-" * 80)

    try:
        # Connect to Temporal
        print("Connecting to Temporal server...")
        client = await create_temporal_client()
        print("✅ Connected successfully!")
        print("-" * 80)

        # Start the EventWorkflow
        print("Starting EventWorkflow...")
        handle = await client.start_workflow(
            EventWorkflow.run,
            args=[workflow_id, config_path],
            id=workflow_id,
            task_queue=task_queue,
        )

        print(f"✅ EventWorkflow started successfully!")
        print(f"Workflow ID: {handle.id}")
        print(f"Run ID: {handle.result_run_id}")
        print("-" * 80)
        print("\nWorkflow is now running. You can:")
        print(f"  - View it in the Web UI: http://localhost:8233/namespaces/default/workflows/{workflow_id}")
        print(f"  - Query it: temporal workflow query --workflow-id {workflow_id} --name get_event_status")
        print(f"  - Register players via the API: POST http://localhost:8000/api/join")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error starting workflow: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
