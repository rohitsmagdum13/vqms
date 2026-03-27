"""Module: eventbridge
Description: EventBridge publisher for all 17 VQMS event types.

Publishes events to the VQMS EventBridge event bus for decoupled
communication between services. All 17 event types are defined
in the Architecture Doc Section 4.
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


class EventBridgeError(Exception):
    """Raised when EventBridge publishing fails."""


class VQMSEventType(StrEnum):
    """All 17 VQMS EventBridge event types from Architecture Doc Section 4."""

    EMAIL_RECEIVED = "EmailReceived"
    EMAIL_PARSED = "EmailParsed"
    ANALYSIS_COMPLETED = "AnalysisCompleted"
    VENDOR_RESOLVED = "VendorResolved"
    TICKET_CREATED = "TicketCreated"
    TICKET_UPDATED = "TicketUpdated"
    DRAFT_PREPARED = "DraftPrepared"
    VALIDATION_PASSED = "ValidationPassed"
    VALIDATION_FAILED = "ValidationFailed"
    EMAIL_SENT = "EmailSent"
    SLA_WARNING_70 = "SLAWarning70"
    SLA_ESCALATION_85 = "SLAEscalation85"
    SLA_ESCALATION_95 = "SLAEscalation95"
    VENDOR_REPLY_RECEIVED = "VendorReplyReceived"
    RESOLUTION_PREPARED = "ResolutionPrepared"
    TICKET_CLOSED = "TicketClosed"
    TICKET_REOPENED = "TicketReopened"


@dataclass(frozen=True)
class EventBridgeConfig:
    """EventBridge configuration.

    Attributes:
        event_bus_name: Name of the VQMS EventBridge event bus.
        source: Event source identifier.
        region: AWS region.
    """

    event_bus_name: str = "vqms-events"
    source: str = "vqms.pipeline"
    region: str = "us-east-1"


def _build_client(config: EventBridgeConfig | None) -> Any:
    """Build a boto3 EventBridge client from config."""
    cfg = config or EventBridgeConfig()
    return boto3.client("events", region_name=cfg.region)


async def publish_event(
    event_type: VQMSEventType,
    detail: dict[str, Any],
    *,
    config: EventBridgeConfig | None = None,
    correlation_id: str | None = None,
) -> str:
    """Publish an event to the VQMS EventBridge event bus.

    Every side-effect in the pipeline publishes an event for
    downstream consumers and audit trail.

    Args:
        event_type: One of the 17 VQMS event types.
        detail: Event detail payload as a dictionary.
        config: EventBridge configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        EventBridge event ID of the published event.

    Raises:
        EventBridgeError: When event publishing fails.
    """
    cfg = config or EventBridgeConfig()
    if correlation_id is not None:
        detail = {**detail, "correlation_id": correlation_id}
    try:
        client = _build_client(config)
        response = client.put_events(
            Entries=[
                {
                    "Source": cfg.source,
                    "DetailType": str(event_type),
                    "Detail": json.dumps(detail),
                    "EventBusName": cfg.event_bus_name,
                },
            ],
        )
        failed_count = response.get("FailedEntryCount", 0)
        if failed_count > 0:
            entries = response.get("Entries", [])
            error_msg = entries[0].get("ErrorMessage", "unknown")
            msg = (
                f"EventBridge publish failed for "
                f"{event_type}: {error_msg}"
            )
            raise EventBridgeError(msg)

        event_id: str = response["Entries"][0]["EventId"]
        logger.info(
            "eventbridge_event_published",
            extra={
                "event_type": str(event_type),
                "event_id": event_id,
                "event_bus": cfg.event_bus_name,
                "correlation_id": correlation_id,
            },
        )
        return event_id
    except EventBridgeError:
        raise
    except ClientError as exc:
        msg = (
            f"EventBridge publish failed for "
            f"{event_type}: {exc}"
        )
        raise EventBridgeError(msg) from exc


async def publish_batch(
    events: list[tuple[VQMSEventType, dict[str, Any]]],
    *,
    config: EventBridgeConfig | None = None,
    correlation_id: str | None = None,
) -> list[str]:
    """Publish a batch of events to EventBridge.

    EventBridge supports up to 10 entries per put_events call.

    Args:
        events: List of (event_type, detail) tuples to publish.
        config: EventBridge configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of EventBridge event IDs for published events.

    Raises:
        EventBridgeError: When batch publishing fails.
    """
    if not events:
        return []

    cfg = config or EventBridgeConfig()
    entries: list[dict[str, str]] = []
    for event_type, detail in events:
        enriched = (
            {**detail, "correlation_id": correlation_id}
            if correlation_id is not None
            else detail
        )
        entries.append(
            {
                "Source": cfg.source,
                "DetailType": str(event_type),
                "Detail": json.dumps(enriched),
                "EventBusName": cfg.event_bus_name,
            },
        )

    try:
        client = _build_client(config)
        response = client.put_events(Entries=entries)
        failed_count = response.get("FailedEntryCount", 0)
        if failed_count > 0:
            msg = (
                f"EventBridge batch had {failed_count} "
                f"failed entries out of {len(entries)}"
            )
            raise EventBridgeError(msg)

        event_ids: list[str] = [
            entry["EventId"]
            for entry in response.get("Entries", [])
        ]
        logger.info(
            "eventbridge_batch_published",
            extra={
                "count": len(event_ids),
                "event_bus": cfg.event_bus_name,
                "correlation_id": correlation_id,
            },
        )
        return event_ids
    except EventBridgeError:
        raise
    except ClientError as exc:
        msg = f"EventBridge batch publish failed: {exc}"
        raise EventBridgeError(msg) from exc
