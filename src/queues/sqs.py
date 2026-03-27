"""Module: sqs
Description: SQS producer/consumer for all 10 VQMS queues plus DLQ.

Manages message sending, receiving, and dead-letter queue handling
for the VQMS pipeline. All queues use vqms-dlq as their DLQ.
Queue names from Architecture Doc Section 4.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SQSError(Exception):
    """Raised when SQS operations fail."""


class VQMSQueue(StrEnum):
    """All 10 VQMS SQS queues plus DLQ from Architecture Doc Section 4."""

    EMAIL_INTAKE = "vqms-email-intake"
    ANALYSIS = "vqms-analysis"
    VENDOR_RESOLUTION = "vqms-vendor-resolution"
    TICKET_OPS = "vqms-ticket-ops"
    ROUTING = "vqms-routing"
    COMMUNICATION = "vqms-communication"
    ESCALATION = "vqms-escalation"
    HUMAN_REVIEW = "vqms-human-review"
    AUDIT = "vqms-audit"
    DLQ = "vqms-dlq"


@dataclass(frozen=True)
class SQSConfig:
    """SQS client configuration.

    Attributes:
        region: AWS region.
        max_receive_count: Max receives before message goes to DLQ.
        visibility_timeout_seconds: Message visibility timeout.
        endpoint_url: Optional custom endpoint (for local development).
    """

    region: str = "us-east-1"
    max_receive_count: int = 3
    visibility_timeout_seconds: int = 300
    endpoint_url: str | None = None


def _build_client(config: SQSConfig | None) -> Any:
    """Build a boto3 SQS client from config."""
    cfg = config or SQSConfig()
    kwargs: dict[str, Any] = {"region_name": cfg.region}
    if cfg.endpoint_url is not None:
        kwargs["endpoint_url"] = cfg.endpoint_url
    return boto3.client("sqs", **kwargs)


def _get_queue_url(
    client: Any,
    queue: VQMSQueue,
) -> str:
    """Resolve SQS queue name to URL."""
    response = client.get_queue_url(QueueName=str(queue))
    return response["QueueUrl"]  # type: ignore[no-any-return]


async def send_message(
    queue: VQMSQueue,
    body: dict[str, Any],
    *,
    message_group_id: str | None = None,
    deduplication_id: str | None = None,
    config: SQSConfig | None = None,
    correlation_id: str | None = None,
) -> str:
    """Send a message to an SQS queue.

    Args:
        queue: Target VQMS SQS queue.
        body: Message body as a dictionary (serialized to JSON).
        message_group_id: Optional FIFO queue message group ID.
        deduplication_id: Optional deduplication ID for idempotency.
        config: SQS client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        SQS message ID of the sent message.

    Raises:
        SQSError: When message sending fails.
    """
    try:
        client = _build_client(config)
        queue_url = _get_queue_url(client, queue)
        send_kwargs: dict[str, Any] = {
            "QueueUrl": queue_url,
            "MessageBody": json.dumps(body),
        }
        if message_group_id is not None:
            send_kwargs["MessageGroupId"] = message_group_id
        if deduplication_id is not None:
            send_kwargs["MessageDeduplicationId"] = deduplication_id

        response = client.send_message(**send_kwargs)
        message_id: str = response["MessageId"]
        logger.info(
            "sqs_message_sent",
            extra={
                "queue": str(queue),
                "message_id": message_id,
                "correlation_id": correlation_id,
            },
        )
        return message_id
    except ClientError as exc:
        msg = f"SQS send failed for {queue}: {exc}"
        raise SQSError(msg) from exc


async def receive_messages(
    queue: VQMSQueue,
    *,
    max_messages: int = 10,
    wait_time_seconds: int = 20,
    config: SQSConfig | None = None,
    correlation_id: str | None = None,
) -> list[dict[str, Any]]:
    """Receive messages from an SQS queue using long polling.

    Args:
        queue: Source VQMS SQS queue.
        max_messages: Maximum messages to receive (1-10).
        wait_time_seconds: Long polling wait time in seconds.
        config: SQS client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of message dictionaries with body, receipt_handle, etc.

    Raises:
        SQSError: When message receiving fails.
    """
    try:
        client = _build_client(config)
        queue_url = _get_queue_url(client, queue)
        response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=min(max_messages, 10),
            WaitTimeSeconds=wait_time_seconds,
        )
        raw_messages = response.get("Messages", [])
        result: list[dict[str, Any]] = [
            {
                "message_id": msg["MessageId"],
                "receipt_handle": msg["ReceiptHandle"],
                "body": json.loads(msg["Body"]),
            }
            for msg in raw_messages
        ]
        logger.debug(
            "sqs_messages_received",
            extra={
                "queue": str(queue),
                "count": len(result),
                "correlation_id": correlation_id,
            },
        )
        return result
    except ClientError as exc:
        msg = f"SQS receive failed for {queue}: {exc}"
        raise SQSError(msg) from exc


async def delete_message(
    queue: VQMSQueue,
    receipt_handle: str,
    *,
    config: SQSConfig | None = None,
    correlation_id: str | None = None,
) -> None:
    """Delete a message from an SQS queue after successful processing.

    Args:
        queue: Source VQMS SQS queue.
        receipt_handle: Receipt handle from receive_messages.
        config: SQS client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Raises:
        SQSError: When message deletion fails.
    """
    try:
        client = _build_client(config)
        queue_url = _get_queue_url(client, queue)
        client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
        )
        logger.info(
            "sqs_message_deleted",
            extra={
                "queue": str(queue),
                "correlation_id": correlation_id,
            },
        )
    except ClientError as exc:
        msg = f"SQS delete failed for {queue}: {exc}"
        raise SQSError(msg) from exc


async def get_dlq_messages(
    *,
    max_messages: int = 10,
    config: SQSConfig | None = None,
    correlation_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve messages from the dead-letter queue for inspection.

    Args:
        max_messages: Maximum messages to receive.
        config: SQS client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of DLQ message dictionaries.

    Raises:
        SQSError: When DLQ retrieval fails.
    """
    return await receive_messages(
        VQMSQueue.DLQ,
        max_messages=max_messages,
        wait_time_seconds=0,
        config=config,
        correlation_id=correlation_id,
    )
