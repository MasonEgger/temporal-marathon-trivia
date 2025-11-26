# ABOUTME: EventWorkflow manages entire event lifecycle.
# Coordinates daily child workflows and handles player registration.

import asyncio
from datetime import date, datetime, timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    # Pre-import pydantic dependencies to avoid sandbox warnings
    import annotated_types  # noqa: F401
    import email_validator  # noqa: F401
    import idna  # noqa: F401
    import idna.uts46data  # noqa: F401
    import pydantic_core  # noqa: F401

    from src.activities.config import ConfigActivities
    from src.activities.email import EmailActivities
    from src.activities.moderation import ModerationActivities
    from src.activities.questions import QuestionsActivities
    from src.activities.time import TimeActivities
    from src.models.answer import (
        CreateTimezoneAwareDatetimeRequest,
        EventStatusResponse,
        RegisterPlayerRequest,
    )
    from src.models.question import Question
    from src.models.state import EventState
    from src.workflows.daily import DailyWorkflow
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
        config = await workflow.execute_activity_method(
            ConfigActivities.load_event_config,
            args=[config_path],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Validate questions file via activity
        await workflow.execute_activity_method(
            QuestionsActivities.validate_questions_file,
            args=[config.questions_file_path, config],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Initialize workflow state
        self.state = EventState(
            event_id=event_id,
            config=config,
        )

        # Schedule daily child workflows for each event day
        # Create scheduling tasks but don't await them (they run in background)
        scheduling_tasks = []
        all_dates = config.get_all_dates()
        for day_num, event_date in enumerate(all_dates, start=1):
            task = asyncio.create_task(self._schedule_daily_workflow(event_date, day_num))
            scheduling_tasks.append(task)

        # Keep workflow running indefinitely to manage event
        await workflow.wait_condition(lambda: False)

    async def _schedule_daily_workflow(self, event_date: date, day_num: int) -> None:
        """Schedule and start a DailyWorkflow for a specific event date.

        This helper method calculates the start datetime for the given event date,
        waits until that time (using workflow timers), loads questions for that day,
        and starts a DailyWorkflow child workflow.

        Args:
            event_date: The date for which to schedule the DailyWorkflow.

        Raises:
            ActivityError: If loading questions fails.
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        # Create timezone-aware start datetime via activity
        # (ZoneInfo is restricted in workflow sandbox)
        time_request = CreateTimezoneAwareDatetimeRequest(
            date_str=event_date.isoformat(),
            time_hour=self.state.config.day_start_time.hour,
            time_minute=self.state.config.day_start_time.minute,
            timezone=self.state.config.timezone,
        )
        start_datetime: datetime = await workflow.execute_activity_method(
            TimeActivities.create_timezone_aware_datetime,
            time_request,
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Wait until the start time using workflow timer
        current_time = workflow.now()
        if start_datetime > current_time:
            wait_duration = start_datetime - current_time
            await asyncio.sleep(wait_duration.total_seconds())

        # Load questions for this date via activity
        questions: list[Question] = await workflow.execute_activity_method(
            QuestionsActivities.get_questions_for_day,
            args=[self.state.config.questions_file_path, event_date.isoformat()],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Generate workflow ID for this daily workflow (e.g., "marathon-trivia-event-day-2025-11-26")
        date_str = event_date.isoformat()
        daily_workflow_id = f"{self.state.event_id}-day-{date_str}"

        # Start DailyWorkflow as child workflow
        await workflow.start_child_workflow(
            DailyWorkflow.run,
            args=[date_str, questions, self.state.config],
            id=daily_workflow_id,
            task_queue=workflow.info().task_queue,
        )

        # Store workflow_id in daily_workflow_ids
        self.state.daily_workflow_ids[date_str] = daily_workflow_id

    @workflow.query
    def get_event_status(self) -> EventStatusResponse:
        """Query to get current event status.

        Returns an EventStatusResponse containing event_id, player_count, and daily_workflow_ids
        for monitoring the event progress.

        Returns:
            EventStatusResponse with event metadata and daily workflow IDs.

        Raises:
            RuntimeError: If workflow state is not initialized.

        Example:
            >>> status = await handle.query(EventWorkflow.get_event_status)
            >>> print(f"Event: {status.event_id}, Players: {status.player_count}")
            Event: my-event, Players: 0
            >>> print(f"Daily workflows: {len(status.daily_workflow_ids)}")
            Daily workflows: 3
        """
        if self.state is None:
            raise RuntimeError("Workflow state not initialized")

        return EventStatusResponse(
            event_id=self.state.event_id,
            player_count=self.state.player_count,
            daily_workflow_ids=dict(self.state.daily_workflow_ids),
        )

    @workflow.update
    async def register_player(self, request: RegisterPlayerRequest) -> str:
        """Register a new player and create PlayerEntityWorkflow instance.

        This update handler validates the email, checks for duplicates, and creates
        a child PlayerEntityWorkflow for the player. If the email already exists,
        returns the existing player_id without creating a new workflow.

        Args:
            request: RegisterPlayerRequest containing email, first_name, last_name, company_name

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

        # Moderate first_name for profanity
        workflow.logger.info(f"Moderating first name: '{request.first_name}'")
        first_name_is_profane = await workflow.execute_activity_method(
            ModerationActivities.moderate_player_name,
            request.first_name,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )

        if first_name_is_profane:
            error_msg = f"First name '{request.first_name}' is inappropriate"
            workflow.logger.error(error_msg)
            raise ApplicationError(error_msg, type="InvalidPlayerName")

        # Moderate last_name for profanity
        workflow.logger.info(f"Moderating last name: '{request.last_name}'")
        last_name_is_profane = await workflow.execute_activity_method(
            ModerationActivities.moderate_player_name,
            request.last_name,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )

        if last_name_is_profane:
            error_msg = f"Last name '{request.last_name}' is inappropriate"
            workflow.logger.error(error_msg)
            raise ApplicationError(error_msg, type="InvalidPlayerName")

        workflow.logger.info(f"Names '{request.first_name} {request.last_name}' passed moderation")

        # Validate email via activity
        is_valid = await workflow.execute_activity_method(
            EmailActivities.validate_email,
            args=[request.email, self.state.config.require_work_email],
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Raise ApplicationError if email is invalid
        if not is_valid:
            if self.state.config.require_work_email:
                raise ApplicationError(
                    "Please use a work email address. Personal email domains (gmail, yahoo, etc.) are not allowed."
                )
            else:
                raise ApplicationError(f"Invalid email address: {request.email}")

        # Validate company_name if required
        if self.state.config.require_company_name:
            if not request.company_name or request.company_name.strip() == "":
                raise ApplicationError("Company name is required")

        # Generate meaningful player_id using initials (e.g., "test-player-AS" for Alice Smith)
        first_initial = request.first_name[0].upper() if request.first_name else "X"
        last_initial = request.last_name[0].upper() if request.last_name else "X"
        base_player_id = f"{self.state.event_id}-player-{first_initial}{last_initial}"

        # Add UUID suffix to ensure uniqueness (multiple players with same initials)
        player_id = f"{base_player_id}-{str(workflow.uuid4())[:8]}"

        # Start PlayerEntityWorkflow as child workflow
        # Await the start but don't await the handle (runs indefinitely)
        await workflow.start_child_workflow(
            PlayerEntityWorkflow.run,
            args=[player_id, request.email, request.first_name, request.last_name, request.company_name],
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
