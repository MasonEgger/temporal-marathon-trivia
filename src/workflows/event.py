# ABOUTME: EventWorkflow manages entire event lifecycle.
# Coordinates daily child workflows and handles player registration.

from datetime import timedelta

from temporalio import workflow

from src.activities.config import ConfigActivities
from src.activities.questions import QuestionsActivities
from src.models.state import EventState


@workflow.defn
class EventWorkflow:
    """EventWorkflow manages the entire event lifecycle.

    This workflow is the parent workflow that coordinates the entire trivia event.
    It loads configuration, validates questions, and will later manage daily child
    workflows and player registration.

    State:
        self.state: EventState containing event_id, config, player registry, etc.

    Queries:
        get_event_status() -> dict: Returns event status including event_id and player_count.

    Example:
        >>> # Start EventWorkflow
        >>> handle = await client.start_workflow(
        ...     EventWorkflow.run,
        ...     args=["my-event-123", "config/event.toml"],
        ...     id="event-my-event-123",
        ...     task_queue="marathon-trivia",
        ... )
        >>> # Query event status
        >>> status = await handle.query(EventWorkflow.get_event_status)
        >>> print(status["event_id"])
        my-event-123
    """

    def __init__(self) -> None:
        """Initialize EventWorkflow with empty state."""
        self.state: EventState | None = None

    @workflow.run
    async def run(self, event_id: str, config_path: str) -> None:
        """Run the EventWorkflow to manage the entire event lifecycle.

        This method loads the event configuration, validates the questions file,
        and initializes the workflow state. The workflow runs indefinitely to
        manage the event.

        Args:
            event_id: Unique identifier for this event.
            config_path: Path to the TOML configuration file.

        Raises:
            ActivityError: If config loading or questions validation fails.

        Example:
            >>> await client.start_workflow(
            ...     EventWorkflow.run,
            ...     args=["my-event", "config/event.toml"],
            ...     id="event-my-event",
            ...     task_queue="marathon-trivia",
            ... )
        """
        # Load event configuration via activity
        config_activities = ConfigActivities()
        config = await workflow.execute_activity_method(
            config_activities.load_event_config,
            args=[config_path],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Validate questions file via activity
        questions_activities = QuestionsActivities()
        await workflow.execute_activity_method(
            questions_activities.validate_questions_file,
            args=[config.questions_file_path, config],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Initialize workflow state
        self.state = EventState(
            event_id=event_id,
            config=config,
        )

        # Keep workflow running indefinitely to manage event
        await workflow.wait_condition(lambda: False)

    @workflow.query
    def get_event_status(self) -> dict[str, str | int]:
        """Query to get current event status.

        Returns a dictionary containing event_id and player_count for monitoring
        the event progress.

        Returns:
            dict with keys:
                - event_id (str): Unique identifier for this event.
                - player_count (int): Total number of registered players.

        Raises:
            RuntimeError: If workflow state is not initialized.

        Example:
            >>> status = await handle.query(EventWorkflow.get_event_status)
            >>> print(f"Event: {status['event_id']}, Players: {status['player_count']}")
            Event: my-event, Players: 0
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        return {
            "event_id": self.state.event_id,
            "player_count": self.state.player_count,
        }
