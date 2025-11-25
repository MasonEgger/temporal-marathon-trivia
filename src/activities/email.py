# ABOUTME: Email validation activities for player registration.
# Validates email format and optionally blocks consumer email domains.

import re

from temporalio import activity

# Consumer email domains to block when require_work_email is True
CONSUMER_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
}


class EmailActivities:
    """Activity class for email validation operations."""

    @activity.defn
    def validate_email(self, email: str, require_work_email: bool) -> bool:
        """Validate email format and optionally block consumer domains.

        Uses simple RFC 5322 email format validation via regex. If
        require_work_email is True, blocks common consumer email domains
        (gmail, yahoo, hotmail, outlook, aol, icloud).

        Args:
            email: Email address to validate
            require_work_email: If True, block consumer email domains

        Returns:
            True if email is valid and passes domain check, False otherwise

        Examples:
            >>> activities = EmailActivities()
            >>> activities.validate_email("john@company.com", True)
            True
            >>> activities.validate_email("user@gmail.com", True)
            False
            >>> activities.validate_email("user@gmail.com", False)
            True
        """
        # Handle empty string gracefully
        if not email:
            return False

        # Simple RFC 5322 email format validation
        # Pattern: local-part@domain
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        try:
            if not re.match(email_pattern, email):
                return False

            # Extract domain (part after @)
            domain = email.split("@")[1].lower()

            # If require_work_email is True, check domain not in CONSUMER_DOMAINS
            if require_work_email and domain in CONSUMER_DOMAINS:
                return False

            return True

        except Exception:
            # Handle any unexpected errors gracefully
            return False
