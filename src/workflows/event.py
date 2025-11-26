# ABOUTME: EventWorkflow manages entire event lifecycle.
# Coordinates daily child workflows and handles player registration.

from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from src.activities.config import ConfigActivities
from src.activities.email import EmailActivities
from src.activities.questions import QuestionsActivities
from src.models.answer import RegisterPlayerRequest
from src.models.state import EventState
from src.workflows.player import PlayerEntityWorkflow


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

    @workflow.update
    async def register_player(self, request: RegisterPlayerRequest) -> str:
        """Register a new player and create PlayerEntityWorkflow instance.

        This update handler validates the email, checks for duplicates, and creates
        a child PlayerEntityWorkflow for the player. If the email already exists,
        returns the existing player_id without creating a new workflow.

        Args:
            request: RegisterPlayerRequest containing email, first_name, last_name

        Returns:
            player_id: UUID string identifying the player's workflow.

        Raises:
            RuntimeError: If workflow state is not initialized.
            ApplicationError: If email validation fails.

        Example:
            >>> request = RegisterPlayerRequest(
            ...     email="john.doe@company.com",
            ...     first_name="John",
            ...     last_name="Doe"
            ... )
            >>> player_id = await handle.execute_update(
            ...     EventWorkflow.register_player, request
            ... )
            >>> print(f"Registered player: {player_id}")
            Registered player: 550e8400-e29b-41d4-a716-446655440000
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Check if email already registered (handle duplicates)
        if request.email in self.state.player_registry:
            # Return existing player_id for duplicate email
            return self.state.player_registry[request.email]

        # Validate email via activity
        email_activities = EmailActivities()
        is_valid = await workflow.execute_activity_method(
            email_activities.validate_email,
            args=[request.email, self.state.config.require_work_email],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Raise ApplicationError if email is invalid
        if not is_valid:
            raise ApplicationError(f"Invalid email address: {request.email}")

        # Generate new player_id using workflow.uuid4()
        player_id = str(workflow.uuid4())

        # Start PlayerEntityWorkflow as child workflow
        # Await the start but don't await the handle (runs indefinitely)
        await workflow.start_child_workflow(
            PlayerEntityWorkflow.run,
            args=[player_id, request.email, request.first_name, request.last_name],
            id=player_id,  # Use player_id as workflow_id for idempotency
            task_queue=workflow.info().task_queue,
        )

        # Store email -> player_id mapping in registry
        self.state.player_registry[request.email] = player_id

        # Increment player_count
        self.state.player_count += 1

        # Return player_id
        return player_id

    @workflow.query
    def get_player_id_by_email(self, email: str) -> str | None:
        """Query to get player_id by email address.

        Returns the player_id if the email is registered, otherwise None.
        This is useful for looking up existing players by email.

        Args:
            email: Email address to look up

        Returns:
            player_id if email is registered, None otherwise

        Example:
            >>> player_id = await handle.query(
            ...     EventWorkflow.get_player_id_by_email,
            ...     "john.doe@company.com"
            ... )
            >>> if player_id:
            ...     print(f"Found player: {player_id}")
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        return self.state.player_registry.get(email)
