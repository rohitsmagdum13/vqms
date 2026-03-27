"""Module: validation
Description: Input validation helpers for the VQMS pipeline.

Provides validation functions for system boundary inputs:
email addresses, ticket numbers, vendor IDs, and other
external data per Coding Standards Section 1.1.
"""

from __future__ import annotations

import logging
import re
import uuid

from email_validator import EmailNotValidError, validate_email

logger = logging.getLogger(__name__)

# ServiceNow incident number: INC followed by 7-10 digits
_TICKET_PATTERN = re.compile(r"^INC\d{7,10}$")

# Salesforce Account ID: starts with 001, 15 or 18 alphanumeric chars
_SALESFORCE_ID_PATTERN = re.compile(r"^001[a-zA-Z0-9]{12}([a-zA-Z0-9]{3})?$")

# PII redaction patterns
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")


class ValidationError(Exception):
    """Raised when input validation fails."""


def validate_email_address(email: str) -> bool:
    """Validate an email address format.

    Args:
        email: Email address to validate.

    Returns:
        True if the email format is valid.

    Raises:
        ValidationError: When validation logic fails.
    """
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return False
    return True


def validate_ticket_number(ticket_number: str) -> bool:
    """Validate a ServiceNow ticket number format (e.g., INC0012345).

    Args:
        ticket_number: Ticket number to validate.

    Returns:
        True if the ticket number format is valid.

    Raises:
        ValidationError: When validation logic fails.
    """
    return bool(_TICKET_PATTERN.match(ticket_number))


def validate_correlation_id(correlation_id: str) -> bool:
    """Validate a correlation ID format (UUID v4).

    Args:
        correlation_id: Correlation ID to validate.

    Returns:
        True if the correlation ID format is valid.

    Raises:
        ValidationError: When validation logic fails.
    """
    try:
        parsed = uuid.UUID(correlation_id, version=4)
    except (ValueError, AttributeError):
        return False
    return str(parsed) == correlation_id


def validate_vendor_id(vendor_id: str) -> bool:
    """Validate a Salesforce Account ID format.

    Args:
        vendor_id: Salesforce Account ID to validate.

    Returns:
        True if the vendor ID format is valid.

    Raises:
        ValidationError: When validation logic fails.
    """
    return bool(_SALESFORCE_ID_PATTERN.match(vendor_id))


def sanitize_for_log(text: str) -> str:
    """Sanitize text for safe inclusion in structured logs.

    Removes potential PII and sensitive data patterns.
    Never log secrets per Section 10.

    Args:
        text: Text to sanitize.

    Returns:
        Sanitized text safe for logging.

    Raises:
        ValidationError: When sanitization fails.
    """
    sanitized = _EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    sanitized = _SSN_PATTERN.sub("[SSN_REDACTED]", sanitized)
    sanitized = _CREDIT_CARD_PATTERN.sub("[CC_REDACTED]", sanitized)
    return sanitized
