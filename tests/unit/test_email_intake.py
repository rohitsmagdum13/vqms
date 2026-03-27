"""Unit tests for the Email Ingestion Service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.models.email import EmailDirection
from src.services.email_intake import (
    EmailIntakeError,
    fetch_emails,
    ingest_email,
    parse_email,
)


def _raw_graph_email(
    *,
    msg_id: str = "AAMkAGI2TG93AAA=",
    subject: str = "Invoice Query",
    sender: str = "vendor@example.com",
    has_attachments: bool = False,
) -> dict[str, object]:
    """Build a realistic Graph API email payload."""
    result: dict[str, object] = {
        "id": msg_id,
        "internetMessageId": f"<{msg_id}@example.com>",
        "conversationId": "conv-001",
        "subject": subject,
        "from": {
            "emailAddress": {
                "address": sender,
                "name": "Test Vendor",
            },
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": "support@hexaware.com",
                },
            },
        ],
        "receivedDateTime": "2026-03-27T10:00:00Z",
        "hasAttachments": has_attachments,
        "body": {
            "contentType": "text",
            "content": "Please check invoice #12345.",
        },
        "internetMessageHeaders": [
            {"name": "From", "value": sender},
        ],
    }
    return result


def _raw_reply_email() -> dict[str, object]:
    """Build a Graph API email that is a reply."""
    email = _raw_graph_email(msg_id="reply-001")
    email["internetMessageHeaders"] = [
        {
            "name": "In-Reply-To",
            "value": "<original@example.com>",
        },
        {
            "name": "References",
            "value": "<original@example.com> <second@example.com>",
        },
    ]
    return email


class TestParseEmail:
    """Tests for parse_email."""

    @pytest.mark.asyncio
    async def test_parse_extracts_plain_text(self) -> None:
        raw = _raw_graph_email()
        parsed = await parse_email(raw, correlation_id="cid-1")
        assert parsed.message_id == "AAMkAGI2TG93AAA="
        assert "invoice #12345" in parsed.plain_text_body
        assert parsed.html_body is None
        assert parsed.is_reply is False

    @pytest.mark.asyncio
    async def test_parse_extracts_html(self) -> None:
        raw = _raw_graph_email()
        raw["body"] = {
            "contentType": "html",
            "content": "<p>HTML body</p>",
        }
        parsed = await parse_email(raw)
        assert parsed.html_body == "<p>HTML body</p>"
        assert parsed.plain_text_body == ""

    @pytest.mark.asyncio
    async def test_parse_detects_reply(self) -> None:
        raw = _raw_reply_email()
        parsed = await parse_email(raw)
        assert parsed.is_reply is True
        assert parsed.in_reply_to == "<original@example.com>"
        assert len(parsed.references) == 2

    @pytest.mark.asyncio
    async def test_parse_handles_missing_headers(self) -> None:
        raw = _raw_graph_email()
        raw.pop("internetMessageHeaders", None)
        parsed = await parse_email(raw)
        assert parsed.is_reply is False
        assert parsed.headers == {}

    @pytest.mark.asyncio
    async def test_parse_generates_correlation_id(self) -> None:
        raw = _raw_graph_email()
        parsed = await parse_email(raw)
        assert parsed.correlation_id is not None
        assert len(parsed.correlation_id) > 0


class TestFetchEmails:
    """Tests for fetch_emails."""

    @pytest.mark.asyncio
    async def test_fetch_returns_messages(self) -> None:
        mock_messages = [
            _raw_graph_email(msg_id="msg-1"),
            _raw_graph_email(msg_id="msg-2"),
        ]
        with patch(
            "src.services.email_intake.fetch_messages",
            new_callable=AsyncMock,
            return_value=mock_messages,
        ):
            from src.adapters.graph_api import GraphAPIConfig

            config = GraphAPIConfig(
                tenant_id="t", client_id="c",
            )
            result = await fetch_emails(
                mailbox_id="test@example.com",
                graph_config=config,
                correlation_id="cid",
            )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_fetch_wraps_error(self) -> None:
        with patch(
            "src.services.email_intake.fetch_messages",
            new_callable=AsyncMock,
            side_effect=Exception("connection failed"),
        ):
            from src.adapters.graph_api import GraphAPIConfig

            config = GraphAPIConfig(
                tenant_id="t", client_id="c",
            )
            with pytest.raises(
                EmailIntakeError, match="Failed to fetch",
            ):
                await fetch_emails(
                    mailbox_id="test@example.com",
                    graph_config=config,
                )


class TestIngestEmail:
    """Tests for the full ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_ingest_new_email(self) -> None:
        raw = _raw_graph_email()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()

        with (
            patch(
                "src.services.email_intake.upload_object",
                new_callable=AsyncMock,
                return_value="2026/03/27/msg.eml",
            ),
            patch(
                "src.services.email_intake.eb_publish",
                new_callable=AsyncMock,
                return_value="event-id-1",
            ),
            patch(
                "src.services.email_intake.sqs_send",
                new_callable=AsyncMock,
                return_value="sqs-msg-id-1",
            ),
        ):
            result = await ingest_email(
                raw,
                redis_client=mock_redis,
                correlation_id="cid-ingest",
            )

        assert result.is_duplicate is False
        assert result.email_message.message_id == "AAMkAGI2TG93AAA="
        assert result.email_message.sender_email == "vendor@example.com"
        assert result.email_message.direction == EmailDirection.INBOUND
        assert result.s3_raw_key != ""
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_duplicate_returns_early(self) -> None:
        raw = _raw_graph_email()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            return_value="AAMkAGI2TG93AAA=",
        )

        result = await ingest_email(
            raw,
            redis_client=mock_redis,
            correlation_id="cid-dup",
        )
        assert result.is_duplicate is True
        assert result.s3_raw_key == ""

    @pytest.mark.asyncio
    async def test_ingest_without_redis(self) -> None:
        raw = _raw_graph_email()
        with (
            patch(
                "src.services.email_intake.upload_object",
                new_callable=AsyncMock,
                return_value="key.eml",
            ),
            patch(
                "src.services.email_intake.eb_publish",
                new_callable=AsyncMock,
                return_value="eid",
            ),
            patch(
                "src.services.email_intake.sqs_send",
                new_callable=AsyncMock,
                return_value="sid",
            ),
        ):
            result = await ingest_email(
                raw, redis_client=None,
            )
        assert result.is_duplicate is False

    @pytest.mark.asyncio
    async def test_ingest_builds_correct_model(self) -> None:
        raw = _raw_graph_email(
            subject="Test Subject",
            sender="user@corp.com",
        )
        with (
            patch(
                "src.services.email_intake.upload_object",
                new_callable=AsyncMock,
                return_value="key.eml",
            ),
            patch(
                "src.services.email_intake.eb_publish",
                new_callable=AsyncMock,
                return_value="eid",
            ),
            patch(
                "src.services.email_intake.sqs_send",
                new_callable=AsyncMock,
                return_value="sid",
            ),
        ):
            result = await ingest_email(raw)

        msg = result.email_message
        assert msg.subject == "Test Subject"
        assert msg.sender_email == "user@corp.com"
        assert msg.conversation_id == "conv-001"
        assert len(msg.recipients) == 1
        assert msg.recipients[0] == "support@hexaware.com"
