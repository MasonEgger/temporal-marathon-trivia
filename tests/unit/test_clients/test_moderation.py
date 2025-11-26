# ABOUTME: Unit tests for the PurgoMalum moderation client.
# Tests verify helper functions for URL building and response parsing.

import pytest

from src.clients.moderation import build_moderation_url, parse_profanity_response


class TestParseProfanityResponse:
    """Test suite for parse_profanity_response helper function."""

    def test_parse_true_response(self) -> None:
        """Test parsing 'true' response returns True."""
        result = parse_profanity_response("true")
        assert result is True

    def test_parse_false_response(self) -> None:
        """Test parsing 'false' response returns False."""
        result = parse_profanity_response("false")
        assert result is False

    def test_parse_true_with_whitespace(self) -> None:
        """Test parsing 'true' with surrounding whitespace."""
        result = parse_profanity_response("  true  ")
        assert result is True

    def test_parse_false_with_whitespace(self) -> None:
        """Test parsing 'false' with surrounding whitespace."""
        result = parse_profanity_response("  false  ")
        assert result is False

    def test_parse_uppercase_true(self) -> None:
        """Test parsing uppercase 'TRUE' response."""
        result = parse_profanity_response("TRUE")
        assert result is True

    def test_parse_uppercase_false(self) -> None:
        """Test parsing uppercase 'FALSE' response."""
        result = parse_profanity_response("FALSE")
        assert result is False

    def test_parse_mixed_case(self) -> None:
        """Test parsing mixed case 'TrUe' response."""
        result = parse_profanity_response("TrUe")
        assert result is True

    def test_parse_invalid_response_raises_error(self) -> None:
        """Test that invalid response raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_profanity_response("invalid")
        assert "Invalid profanity response" in str(exc_info.value)

    def test_parse_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_profanity_response("")
        assert "Invalid profanity response" in str(exc_info.value)

    def test_parse_numeric_response_raises_error(self) -> None:
        """Test that numeric response raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_profanity_response("1")
        assert "Invalid profanity response" in str(exc_info.value)


class TestBuildModerationUrl:
    """Test suite for build_moderation_url helper function."""

    def test_build_url_simple_name(self) -> None:
        """Test building URL with simple name."""
        base_url = "https://www.purgomalum.com/service/containsprofanity"
        name = "Alice"

        result = build_moderation_url(base_url, name)

        assert result == f"{base_url}?text=Alice"

    def test_build_url_name_with_space(self) -> None:
        """Test building URL with name containing spaces."""
        base_url = "https://www.purgomalum.com/service/containsprofanity"
        name = "Alice Smith"

        result = build_moderation_url(base_url, name)

        # URL encoding replaces spaces with +
        assert result == f"{base_url}?text=Alice+Smith"

    def test_build_url_name_with_special_characters(self) -> None:
        """Test building URL with special characters."""
        base_url = "https://www.purgomalum.com/service/containsprofanity"
        name = "O'Brien"

        result = build_moderation_url(base_url, name)

        # quote_plus encodes apostrophe as %27
        assert result == f"{base_url}?text=O%27Brien"

    def test_build_url_name_with_ampersand(self) -> None:
        """Test building URL with ampersand character."""
        base_url = "https://www.purgomalum.com/service/containsprofanity"
        name = "Smith&Jones"

        result = build_moderation_url(base_url, name)

        # Ampersand should be encoded as %26
        assert result == f"{base_url}?text=Smith%26Jones"

    def test_build_url_empty_name(self) -> None:
        """Test building URL with empty name."""
        base_url = "https://www.purgomalum.com/service/containsprofanity"
        name = ""

        result = build_moderation_url(base_url, name)

        assert result == f"{base_url}?text="

    def test_build_url_unicode_characters(self) -> None:
        """Test building URL with unicode characters."""
        base_url = "https://www.purgomalum.com/service/containsprofanity"
        name = "José"

        result = build_moderation_url(base_url, name)

        # Unicode characters should be percent-encoded
        assert "Jos" in result
        assert "%C3%A9" in result  # é encoded
