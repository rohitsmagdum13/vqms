"""Module: retry
Description: Exponential backoff and circuit breaker utilities for the VQMS pipeline.

Implements retry with exponential backoff for transient errors only
(429, timeouts) and circuit breaker pattern per Coding Standards Section 7.
Never retries permanent errors (400, policy violations).
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""


class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is open."""


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for protecting external service calls.

    Opens after N consecutive failures, rejects calls during
    cool-down period, then enters half-open state to test recovery.

    Attributes:
        name: Circuit breaker name (typically the service name).
        failure_threshold: Number of failures before opening.
        recovery_timeout_seconds: Seconds before half-open transition.
        state: Current circuit state.
        failure_count: Current consecutive failure count.
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: datetime | None = field(default=None, repr=False)


async def retry_with_backoff[T](
    func: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 30.0,
    transient_exceptions: tuple[type[Exception], ...] = (),
    correlation_id: str | None = None,
    **kwargs: Any,
) -> T:
    """Execute a function with exponential backoff retry for transient errors.

    Only retries for transient errors (429, timeouts). Immediately
    raises permanent errors without retrying.

    Args:
        func: Async function to execute.
        *args: Positional arguments for the function.
        max_retries: Maximum number of retry attempts.
        base_delay_seconds: Base delay between retries.
        max_delay_seconds: Maximum delay cap.
        transient_exceptions: Tuple of exception types considered transient.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.
        **kwargs: Keyword arguments for the function.

    Returns:
        Result of the function execution.

    Raises:
        RetryError: When all retry attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except transient_exceptions as exc:
            last_exc = exc
            if attempt == max_retries:
                break
            delay = min(
                base_delay_seconds * (2 ** attempt),
                max_delay_seconds,
            )
            jitter = random.uniform(0, delay * 0.25)  # noqa: S311
            total_delay = delay + jitter
            logger.warning(
                "retry_attempt",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay_seconds": round(total_delay, 3),
                    "error": str(exc),
                    "correlation_id": correlation_id,
                },
            )
            await asyncio.sleep(total_delay)
        except Exception:
            raise

    msg = (
        f"All {max_retries} retries exhausted: {last_exc}"
    )
    raise RetryError(msg) from last_exc


async def check_circuit(
    breaker: CircuitBreaker,
    *,
    correlation_id: str | None = None,
) -> bool:
    """Check if a circuit breaker allows the call to proceed.

    Args:
        breaker: Circuit breaker instance to check.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        True if the call is allowed.

    Raises:
        CircuitBreakerError: When the circuit is open.
    """
    if breaker.state == CircuitState.CLOSED:
        return True

    if breaker.state == CircuitState.HALF_OPEN:
        return True

    # OPEN state — check if recovery timeout has elapsed
    if breaker.last_failure_time is not None:
        elapsed = (
            datetime.now(UTC) - breaker.last_failure_time
        ).total_seconds()
        if elapsed >= breaker.recovery_timeout_seconds:
            breaker.state = CircuitState.HALF_OPEN
            logger.info(
                "circuit_breaker_half_open",
                extra={
                    "breaker": breaker.name,
                    "elapsed_seconds": round(elapsed, 1),
                    "correlation_id": correlation_id,
                },
            )
            return True

    msg = (
        f"Circuit breaker '{breaker.name}' is OPEN "
        f"(failures={breaker.failure_count})"
    )
    raise CircuitBreakerError(msg)


async def record_success(
    breaker: CircuitBreaker,
    *,
    correlation_id: str | None = None,
) -> None:
    """Record a successful call for the circuit breaker.

    Args:
        breaker: Circuit breaker instance.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.
    """
    if breaker.state == CircuitState.HALF_OPEN:
        logger.info(
            "circuit_breaker_closed",
            extra={
                "breaker": breaker.name,
                "correlation_id": correlation_id,
            },
        )
    breaker.failure_count = 0
    breaker.state = CircuitState.CLOSED
    breaker.last_failure_time = None


async def record_failure(
    breaker: CircuitBreaker,
    *,
    correlation_id: str | None = None,
) -> None:
    """Record a failed call for the circuit breaker.

    Args:
        breaker: Circuit breaker instance.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.
    """
    breaker.failure_count += 1
    breaker.last_failure_time = datetime.now(UTC)

    if breaker.failure_count >= breaker.failure_threshold:
        breaker.state = CircuitState.OPEN
        logger.warning(
            "circuit_breaker_opened",
            extra={
                "breaker": breaker.name,
                "failure_count": breaker.failure_count,
                "threshold": breaker.failure_threshold,
                "correlation_id": correlation_id,
            },
        )
