# ABOUTME: Time and date conversion activities for timezone-aware operations.
# Handles timezone conversions that cannot be done in workflow sandbox.

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from temporalio import activity

from src.models.answer import CreateTimezoneAwareDatetimeRequest


class TimeActivities:
    """Activity class for time and date conversion operations."""

    @activity.defn
    def create_timezone_aware_datetime(self, request: CreateTimezoneAwareDatetimeRequest) -> datetime:
        """Create a timezone-aware datetime from date, time components, and timezone.

        This activity handles timezone-aware datetime creation, which cannot be done
        in workflows due to Temporal's sandbox restrictions on ZoneInfo.

        Args:
            request: CreateTimezoneAwareDatetimeRequest with date_str, time_hour,
                     time_minute, and timezone fields

        Returns:
            datetime: Timezone-aware datetime object

        Raises:
            ValueError: If date_str is invalid or timezone is unknown

        Example:
            >>> activities = TimeActivities()
            >>> request = CreateTimezoneAwareDatetimeRequest(
            ...     date_str="2025-03-10",
            ...     time_hour=9,
            ...     time_minute=0,
            ...     timezone="America/Los_Angeles"
            ... )
            >>> dt = activities.create_timezone_aware_datetime(request)
            >>> dt.tzinfo.zone
            'America/Los_Angeles'
        """
        # Parse date string
        event_date = date.fromisoformat(request.date_str)

        # Reconstruct time object from components
        time_obj = time(hour=request.time_hour, minute=request.time_minute)

        # Create timezone-aware datetime
        tz = ZoneInfo(request.timezone)
        aware_datetime = datetime.combine(event_date, time_obj, tzinfo=tz)

        return aware_datetime
