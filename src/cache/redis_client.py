"""Module: redis_client
Description: Redis connection wrapper with key-pattern helpers for the VQMS pipeline.

Manages Redis connections and provides typed key builders for the
6 Redis key families defined in the Architecture Doc Section 4:
idempotency, thread, ticket, workflow, vendor, sla.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisClientError(Exception):
    """Raised when Redis operations fail."""


@dataclass(frozen=True)
class RedisConfig:
    """Redis connection configuration.

    Attributes:
        host: Redis host.
        port: Redis port.
        password: Redis password (required for Redis Cloud).
        db: Redis database number.
        ssl: Whether to use TLS (required for Redis Cloud).
        decode_responses: Whether to decode responses to strings.
    """

    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    ssl: bool = False
    decode_responses: bool = True


# --- Key pattern builders for the 6 Redis key families ---

def idempotency_key(message_id: str) -> str:
    """Build Redis key for email idempotency check.

    Args:
        message_id: Microsoft Graph API message ID.

    Returns:
        Redis key string: idempotency:{message_id}
    """
    return f"idempotency:{message_id}"


def thread_key(conversation_id: str) -> str:
    """Build Redis key for thread correlation data.

    Args:
        conversation_id: Graph API conversation/thread ID.

    Returns:
        Redis key string: thread:{conversation_id}
    """
    return f"thread:{conversation_id}"


def ticket_key(ticket_number: str) -> str:
    """Build Redis key for ticket cache.

    Args:
        ticket_number: ServiceNow ticket number.

    Returns:
        Redis key string: ticket:{ticket_number}
    """
    return f"ticket:{ticket_number}"


def workflow_key(case_id: str) -> str:
    """Build Redis key for workflow state cache.

    Args:
        case_id: Workflow case execution ID.

    Returns:
        Redis key string: workflow:{case_id}
    """
    return f"workflow:{case_id}"


def vendor_key(vendor_id: str) -> str:
    """Build Redis key for vendor profile cache.

    Args:
        vendor_id: Salesforce Account ID.

    Returns:
        Redis key string: vendor:{vendor_id}
    """
    return f"vendor:{vendor_id}"


def sla_key(ticket_number: str) -> str:
    """Build Redis key for SLA monitoring data.

    Args:
        ticket_number: ServiceNow ticket number.

    Returns:
        Redis key string: sla:{ticket_number}
    """
    return f"sla:{ticket_number}"


async def create_client(
    config: RedisConfig,
    *,
    correlation_id: str | None = None,
) -> aioredis.Redis:
    """Create an async Redis client.

    Args:
        config: Redis connection configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        Async Redis client instance.

    Raises:
        RedisClientError: When connection fails.
    """
    try:
        client: aioredis.Redis = aioredis.Redis(
            host=config.host,
            port=config.port,
            password=config.password or None,
            db=config.db,
            ssl=config.ssl,
            decode_responses=config.decode_responses,
        )
        await client.ping()  # type: ignore[misc]
        logger.info(
            "redis_client_created",
            extra={
                "host": config.host,
                "port": config.port,
                "correlation_id": correlation_id,
            },
        )
        return client
    except Exception as exc:
        msg = f"Failed to create Redis client: {exc}"
        raise RedisClientError(msg) from exc


async def close_client(client: Any, *, correlation_id: str | None = None) -> None:
    """Gracefully close the Redis client.

    Args:
        client: Redis client to close.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Raises:
        RedisClientError: When closure fails.
    """
    try:
        await client.aclose()
        logger.info("redis_client_closed", extra={"correlation_id": correlation_id})
    except Exception as exc:
        msg = f"Failed to close Redis client: {exc}"
        raise RedisClientError(msg) from exc


async def health_check(client: Any, *, correlation_id: str | None = None) -> bool:
    """Check Redis connectivity.

    Args:
        client: Redis client to check.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        True if Redis is reachable.

    Raises:
        RedisClientError: When health check fails.
    """
    try:
        result = await client.ping()
        logger.debug(
            "redis_health_check",
            extra={"result": result, "correlation_id": correlation_id},
        )
        return bool(result)
    except Exception as exc:
        msg = f"Redis health check failed: {exc}"
        raise RedisClientError(msg) from exc
