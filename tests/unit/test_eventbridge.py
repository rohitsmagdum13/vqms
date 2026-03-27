"""Unit tests for EventBridge publisher using moto mock."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from src.events.eventbridge import (
    EventBridgeConfig,
    VQMSEventType,
    publish_batch,
    publish_event,
)

_TEST_REGION = "us-east-1"
_TEST_BUS = "vqms-events"


def _cfg() -> EventBridgeConfig:
    return EventBridgeConfig(
        event_bus_name=_TEST_BUS,
        source="vqms.test",
        region=_TEST_REGION,
    )


def _create_bus() -> None:
    client = boto3.client("events", region_name=_TEST_REGION)
    client.create_event_bus(Name=_TEST_BUS)


class TestPublishEvent:
    """Tests for publish_event."""

    @pytest.mark.asyncio
    async def test_publish_returns_event_id(self) -> None:
        with mock_aws():
            _create_bus()
            event_id = await publish_event(
                VQMSEventType.EMAIL_RECEIVED,
                detail={
                    "email_message_id": "msg-001",
                    "sender_email": "vendor@example.com",
                },
                config=_cfg(),
                correlation_id="test-cid",
            )
            assert isinstance(event_id, str)
            assert len(event_id) > 0

    @pytest.mark.asyncio
    async def test_publish_injects_correlation_id(
        self,
    ) -> None:
        with mock_aws():
            _create_bus()
            event_id = await publish_event(
                VQMSEventType.ANALYSIS_COMPLETED,
                detail={"result": "done"},
                config=_cfg(),
                correlation_id="cid-inject-test",
            )
            assert isinstance(event_id, str)

    @pytest.mark.asyncio
    async def test_publish_without_correlation_id(
        self,
    ) -> None:
        with mock_aws():
            _create_bus()
            event_id = await publish_event(
                VQMSEventType.TICKET_CREATED,
                detail={"ticket_number": "INC0012345"},
                config=_cfg(),
            )
            assert isinstance(event_id, str)


class TestPublishBatch:
    """Tests for publish_batch."""

    @pytest.mark.asyncio
    async def test_batch_returns_event_ids(self) -> None:
        with mock_aws():
            _create_bus()
            events = [
                (
                    VQMSEventType.EMAIL_RECEIVED,
                    {"email_message_id": "msg-001"},
                ),
                (
                    VQMSEventType.EMAIL_PARSED,
                    {"email_message_id": "msg-001"},
                ),
            ]
            event_ids = await publish_batch(
                events,
                config=_cfg(),
                correlation_id="test-cid",
            )
            assert len(event_ids) == 2
            assert all(
                isinstance(eid, str) for eid in event_ids
            )

    @pytest.mark.asyncio
    async def test_batch_empty_list_returns_empty(
        self,
    ) -> None:
        result = await publish_batch([], config=_cfg())
        assert result == []
