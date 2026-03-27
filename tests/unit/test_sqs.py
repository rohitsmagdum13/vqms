"""Unit tests for SQS producer/consumer using moto mock."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from src.queues.sqs import (
    SQSConfig,
    SQSError,
    VQMSQueue,
    delete_message,
    get_dlq_messages,
    receive_messages,
    send_message,
)

_TEST_REGION = "us-east-1"
_TEST_QUEUE = VQMSQueue.EMAIL_INTAKE
_TEST_DLQ = VQMSQueue.DLQ


def _cfg() -> SQSConfig:
    return SQSConfig(region=_TEST_REGION)


def _create_queues() -> None:
    client = boto3.client("sqs", region_name=_TEST_REGION)
    client.create_queue(QueueName=str(_TEST_QUEUE))
    client.create_queue(QueueName=str(_TEST_DLQ))


class TestSendMessage:
    """Tests for send_message."""

    @pytest.mark.asyncio
    async def test_send_returns_message_id(self) -> None:
        with mock_aws():
            _create_queues()
            msg_id = await send_message(
                _TEST_QUEUE,
                body={
                    "email_message_id": "msg-001",
                    "status": "new",
                },
                config=_cfg(),
                correlation_id="test-cid",
            )
            assert isinstance(msg_id, str)
            assert len(msg_id) > 0

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_queue_raises(
        self,
    ) -> None:
        with mock_aws():
            with pytest.raises(
                SQSError, match="send failed",
            ):
                await send_message(
                    VQMSQueue.ESCALATION,
                    body={"test": True},
                    config=_cfg(),
                )


class TestReceiveMessages:
    """Tests for receive_messages."""

    @pytest.mark.asyncio
    async def test_receive_returns_sent_message(
        self,
    ) -> None:
        with mock_aws():
            _create_queues()
            await send_message(
                _TEST_QUEUE,
                body={"key": "value"},
                config=_cfg(),
            )
            messages = await receive_messages(
                _TEST_QUEUE,
                max_messages=1,
                wait_time_seconds=0,
                config=_cfg(),
            )
            assert len(messages) == 1
            assert messages[0]["body"]["key"] == "value"
            assert "receipt_handle" in messages[0]
            assert "message_id" in messages[0]

    @pytest.mark.asyncio
    async def test_receive_empty_queue(self) -> None:
        with mock_aws():
            _create_queues()
            messages = await receive_messages(
                _TEST_QUEUE,
                wait_time_seconds=0,
                config=_cfg(),
            )
            assert messages == []


class TestDeleteMessage:
    """Tests for delete_message."""

    @pytest.mark.asyncio
    async def test_delete_after_receive(self) -> None:
        with mock_aws():
            _create_queues()
            await send_message(
                _TEST_QUEUE,
                body={"key": "val"},
                config=_cfg(),
            )
            messages = await receive_messages(
                _TEST_QUEUE,
                wait_time_seconds=0,
                config=_cfg(),
            )
            assert len(messages) == 1
            await delete_message(
                _TEST_QUEUE,
                messages[0]["receipt_handle"],
                config=_cfg(),
            )


class TestGetDlqMessages:
    """Tests for get_dlq_messages."""

    @pytest.mark.asyncio
    async def test_dlq_returns_messages(self) -> None:
        with mock_aws():
            _create_queues()
            await send_message(
                _TEST_DLQ,
                body={"error": "poison message"},
                config=_cfg(),
            )
            dlq_msgs = await get_dlq_messages(
                max_messages=5,
                config=_cfg(),
            )
            assert len(dlq_msgs) == 1
            assert (
                dlq_msgs[0]["body"]["error"] == "poison message"
            )

    @pytest.mark.asyncio
    async def test_dlq_empty(self) -> None:
        with mock_aws():
            _create_queues()
            dlq_msgs = await get_dlq_messages(config=_cfg())
            assert dlq_msgs == []
