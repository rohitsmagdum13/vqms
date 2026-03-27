"""Unit tests for retry with backoff and circuit breaker utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.utils.retry import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    RetryError,
    check_circuit,
    record_failure,
    record_success,
    retry_with_backoff,
)


class _TransientError(Exception):
    """Test-only transient exception."""


class _PermanentError(Exception):
    """Test-only permanent exception."""


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        call_count = 0

        async def succeed() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(
            succeed,
            transient_exceptions=(_TransientError,),
        )
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self) -> None:
        call_count = 0

        async def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _TransientError("transient")
            return "recovered"

        result = await retry_with_backoff(
            fail_then_succeed,
            max_retries=3,
            base_delay_seconds=0.01,
            transient_exceptions=(_TransientError,),
        )
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_retry_error_when_exhausted(self) -> None:
        async def always_fail() -> str:
            raise _TransientError("always fails")

        with pytest.raises(RetryError, match="retries exhausted"):
            await retry_with_backoff(
                always_fail,
                max_retries=2,
                base_delay_seconds=0.01,
                transient_exceptions=(_TransientError,),
            )

    @pytest.mark.asyncio
    async def test_permanent_error_not_retried(self) -> None:
        call_count = 0

        async def permanent_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise _PermanentError("permanent")

        with pytest.raises(_PermanentError):
            await retry_with_backoff(
                permanent_fail,
                max_retries=3,
                base_delay_seconds=0.01,
                transient_exceptions=(_TransientError,),
            )
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_zero_retries_runs_once(self) -> None:
        async def fail() -> str:
            raise _TransientError("fail")

        with pytest.raises(RetryError):
            await retry_with_backoff(
                fail,
                max_retries=0,
                base_delay_seconds=0.01,
                transient_exceptions=(_TransientError,),
            )


class TestCircuitBreaker:
    """Tests for circuit breaker state machine."""

    @pytest.mark.asyncio
    async def test_closed_allows_calls(self) -> None:
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED
        result = await check_circuit(breaker)
        assert result is True

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self) -> None:
        breaker = CircuitBreaker(
            name="test", failure_threshold=3,
        )
        for _ in range(3):
            await record_failure(breaker)
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self) -> None:
        breaker = CircuitBreaker(
            name="test", failure_threshold=2,
        )
        await record_failure(breaker)
        await record_failure(breaker)
        with pytest.raises(CircuitBreakerError, match="OPEN"):
            await check_circuit(breaker)

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self) -> None:
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout_seconds=1,
        )
        await record_failure(breaker)
        assert breaker.state == CircuitState.OPEN

        # Simulate time passing beyond recovery timeout
        breaker.last_failure_time = (
            datetime.now(UTC) - timedelta(seconds=2)
        )
        result = await check_circuit(breaker)
        assert result is True
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_success_closes_from_half_open(self) -> None:
        breaker = CircuitBreaker(name="test")
        breaker.state = CircuitState.HALF_OPEN
        breaker.failure_count = 3
        await record_success(breaker)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        breaker = CircuitBreaker(
            name="test", failure_threshold=5,
        )
        await record_failure(breaker)
        await record_failure(breaker)
        assert breaker.failure_count == 2
        await record_success(breaker)
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_allows_calls(self) -> None:
        breaker = CircuitBreaker(name="test")
        breaker.state = CircuitState.HALF_OPEN
        result = await check_circuit(breaker)
        assert result is True

    @pytest.mark.asyncio
    async def test_failure_below_threshold_stays_closed(
        self,
    ) -> None:
        breaker = CircuitBreaker(
            name="test", failure_threshold=5,
        )
        await record_failure(breaker)
        await record_failure(breaker)
        assert breaker.state == CircuitState.CLOSED
