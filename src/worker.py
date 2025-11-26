# ABOUTME: Temporal worker entry point for Marathon Trivia Platform.
# Registers workflows and activities, connects to Temporal server (local or cloud).

import asyncio
import concurrent.futures
import os
import sys

from temporalio.worker import Worker

from src.activities.config import ConfigActivities
from src.activities.email import EmailActivities
from src.activities.export import ExportActivities
from src.activities.questions import QuestionsActivities
from src.activities.time import TimeActivities
from src.temporal_client import create_temporal_client
from src.workflows.daily import DailyWorkflow
from src.workflows.event import EventWorkflow
from src.workflows.player import PlayerEntityWorkflow


async def main() -> None:
    """Main worker entry point.

    Connects to Temporal server (local or cloud based on environment variables),
    registers all workflows and activities, and runs the worker until interrupted.

    Environment Variables:
        TEMPORAL_ADDRESS: Temporal server address (default: localhost:7233)
        TEMPORAL_NAMESPACE: Temporal namespace (default: default)
        TEMPORAL_TASK_QUEUE: Task queue name (default: marathon-trivia)
        TEMPORAL_TLS_CERT: Path to TLS cert for Temporal Cloud (optional)
        TEMPORAL_TLS_KEY: Path to TLS key for Temporal Cloud (optional)

    Workflows Registered:
        - EventWorkflow: Manages entire event lifecycle
        - DailyWorkflow: Manages single day trivia session
        - PlayerEntityWorkflow: Maintains per-player state

    Activities Registered:
        - ConfigActivities: load_event_config, load_ux_config, validate_questions_file
        - QuestionsActivities: load_questions, get_questions_for_day
        - EmailActivities: validate_email
        - ExportActivities: export_daily_csv_to_s3
        - TimeActivities: create_timezone_aware_datetime

    Returns:
        None

    Raises:
        ConnectionError: If unable to connect to Temporal server
        KeyboardInterrupt: On SIGINT/SIGTERM for graceful shutdown
    """
    # Load configuration from environment
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "marathon-trivia")

    print("=" * 80)
    print("Marathon Trivia Platform - Temporal Worker")
    print("=" * 80)
    print(f"Task Queue: {task_queue}")
    print(f"Temporal Address: {os.getenv('TEMPORAL_ADDRESS', 'localhost:7233')}")
    print(f"Temporal Namespace: {os.getenv('TEMPORAL_NAMESPACE', 'default')}")
    print("-" * 80)

    # Create Temporal client (handles both local and cloud)
    print("Connecting to Temporal server...")
    try:
        client = await create_temporal_client()
        print("✅ Connected successfully!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)

    # Create activity instances
    config_activities = ConfigActivities()
    questions_activities = QuestionsActivities()
    email_activities = EmailActivities()
    export_activities = ExportActivities()
    time_activities = TimeActivities()

    print("-" * 80)
    print("Registering workflows and activities...")
    print()
    print("Workflows:")
    print("  - EventWorkflow (manages entire event lifecycle)")
    print("  - DailyWorkflow (manages single day trivia session)")
    print("  - PlayerEntityWorkflow (maintains per-player state)")
    print()
    print("Activities:")
    print("  - ConfigActivities (2 methods)")
    print("  - QuestionsActivities (3 methods)")
    print("  - EmailActivities (1 method)")
    print("  - ExportActivities (1 method)")
    print("  - TimeActivities (1 method)")
    print("-" * 80)

    # Create worker with ALL workflows and activities
    # Use ThreadPoolExecutor for synchronous activities
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[
                EventWorkflow,
                DailyWorkflow,
                PlayerEntityWorkflow,
            ],
            activities=[
                # ConfigActivities
                config_activities.load_event_config,
                config_activities.load_ux_config,
                # QuestionsActivities
                questions_activities.load_questions,
                questions_activities.get_questions_for_day,
                questions_activities.validate_questions_file,
                # EmailActivities
                email_activities.validate_email,
                # ExportActivities
                export_activities.export_daily_csv_to_s3,
                # TimeActivities
                time_activities.create_timezone_aware_datetime,
            ],
            activity_executor=activity_executor,
        )

        print()
        print("🚀 Worker started successfully!")
        print("Listening for workflow and activity tasks...")
        print("Press Ctrl+C to stop")
        print("=" * 80)

        # Run worker with proper shutdown handling
        # Worker.run() is a blocking call that handles shutdown signals internally
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
