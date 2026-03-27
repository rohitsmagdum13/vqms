"""Module: correlation
Description: Correlation ID generation and propagation for the VQMS pipeline.

Ensures every function in the pipeline accepts and propagates correlation_id
for distributed tracing per the core principle: "Correlation Everywhere."
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

logger = logging.getLogger(__name__)


class CorrelationError(Exception):
    """Raised when correlation ID operations fail."""


# Context variable for implicit correlation ID propagation
_correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)


def generate_correlation_id() -> str:
    """Generate a new UUID v4 correlation ID.

    Returns:
        UUID v4 string for pipeline tracing.

    Raises:
        CorrelationError: When generation fails.
    """
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context.

    Returns:
        Current correlation ID or None if not set.
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in the current context.

    Args:
        correlation_id: Correlation ID to set.
    """
    _correlation_id_var.set(correlation_id)


def ensure_correlation_id(correlation_id: str | None = None) -> str:
    """Ensure a correlation ID exists, generating one if needed.

    If a correlation_id is provided, uses it. Otherwise checks
    the context variable. If neither exists, generates a new one.

    Args:
        correlation_id: Optional explicit correlation ID.

    Returns:
        A valid correlation ID string.

    Raises:
        CorrelationError: When ID resolution fails.
    """
    if correlation_id is not None:
        _correlation_id_var.set(correlation_id)
        return correlation_id

    existing = _correlation_id_var.get()
    if existing is not None:
        return existing

    new_id = generate_correlation_id()
    _correlation_id_var.set(new_id)
    return new_id
