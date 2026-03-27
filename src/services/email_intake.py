"""Module: email_intake
Description: Email Ingestion Service for the VQMS pipeline (Steps 2-3).

Handles Graph API email fetch, MIME parsing, S3 raw storage,
PostgreSQL metadata persistence, Redis idempotency checks,
EventBridge event publishing, and SQS message queuing.
"""

from __future__ import annotations

import base64
import hashlib
import json as _json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.adapters.graph_api import GraphAPIConfig, fetch_messages
from src.cache.redis_client import idempotency_key
from src.events.eventbridge import VQMSEventType
from src.events.eventbridge import publish_event as eb_publish
from src.models.email import (
    EmailAttachment,
    EmailDirection,
    EmailMessage,
    ParsedEmailPayload,
)
from src.queues.sqs import VQMSQueue
from src.queues.sqs import send_message as sqs_send
from src.storage.s3_client import VQMSBucket, upload_object
from src.utils.correlation import ensure_correlation_id
from src.utils.helpers import utc_now

logger = logging.getLogger(__name__)


class EmailIntakeError(Exception):
    """Raised when email ingestion processing fails."""


@dataclass(frozen=True)
class EmailIntakeResult:
    """Result of email ingestion processing.

    Attributes:
        email_message: Persisted email message record.
        parsed_payload: Parsed email content ready for analysis.
        is_duplicate: Whether this email was already processed (idempotent).
        s3_raw_key: S3 key where raw email is stored.
    """

    email_message: EmailMessage
    parsed_payload: ParsedEmailPayload
    is_duplicate: bool
    s3_raw_key: str


async def fetch_emails(
    *,
    mailbox_id: str,
    graph_config: GraphAPIConfig,
    max_results: int = 50,
    correlation_id: str | None = None,
) -> list[dict[str, object]]:
    """Fetch new emails from Microsoft Graph API.

    Polls the configured mailbox using the Graph API adapter for
    unread emails. Supports both webhook and polling hybrid mode.

    Args:
        mailbox_id: Microsoft Graph mailbox identifier.
        graph_config: Graph API configuration with credentials.
        max_results: Maximum number of emails to fetch per poll.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of raw email data dictionaries from Graph API.

    Raises:
        EmailIntakeError: When email fetch fails.
    """
    cid = ensure_correlation_id(correlation_id)
    try:
        messages = await fetch_messages(
            graph_config,
            max_results=max_results,
            filter_unread=True,
            correlation_id=cid,
        )
        logger.info(
            "emails_fetched",
            extra={
                "mailbox_id": mailbox_id,
                "count": len(messages),
                "correlation_id": cid,
            },
        )
        return messages
    except Exception as exc:
        msg = f"Failed to fetch emails: {exc}"
        raise EmailIntakeError(msg) from exc


async def parse_email(
    raw_email: dict[str, object],
    *,
    correlation_id: str | None = None,
) -> ParsedEmailPayload:
    """Parse a raw email into structured ParsedEmailPayload.

    Extracts plain text, HTML body, headers, and attachment metadata
    from Graph API message data. Determines reply-vs-new classification
    using In-Reply-To and References headers.

    Args:
        raw_email: Raw email data from Graph API.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        ParsedEmailPayload with extracted structured content.

    Raises:
        EmailIntakeError: When parsing fails.
    """
    cid = ensure_correlation_id(correlation_id)
    try:
        message_id = str(raw_email.get("id", ""))
        body_obj: Any = raw_email.get("body", {})
        body_content = str(body_obj.get("content", ""))
        body_type = str(body_obj.get("contentType", "text"))

        plain_text = body_content if body_type == "text" else ""
        html_body = body_content if body_type == "html" else None

        # Extract internet message headers if available
        raw_headers: Any = raw_email.get(
            "internetMessageHeaders", [],
        )
        headers: dict[str, str] = {}
        in_reply_to: str | None = None
        references: list[str] = []

        if isinstance(raw_headers, list):
            for hdr in raw_headers:
                name = str(hdr.get("name", ""))
                value = str(hdr.get("value", ""))
                headers[name] = value
                if name.lower() == "in-reply-to":
                    in_reply_to = value
                elif name.lower() == "references":
                    references = value.split()

        is_reply = in_reply_to is not None

        payload = ParsedEmailPayload(
            message_id=message_id,
            plain_text_body=plain_text,
            html_body=html_body,
            headers=headers,
            is_reply=is_reply,
            in_reply_to=in_reply_to,
            references=references,
            correlation_id=cid,
        )
        logger.info(
            "email_parsed",
            extra={
                "message_id": message_id,
                "is_reply": is_reply,
                "has_html": html_body is not None,
                "correlation_id": cid,
            },
        )
        return payload
    except Exception as exc:
        msg = f"Failed to parse email: {exc}"
        raise EmailIntakeError(msg) from exc


async def ingest_email(
    raw_email: dict[str, object],
    *,
    redis_client: Any = None,
    db_pool: Any = None,
    correlation_id: str | None = None,
) -> EmailIntakeResult:
    """Full email ingestion pipeline: parse, deduplicate, store, publish.

    Orchestrates the complete ingestion flow:
    1. Check Redis idempotency key (message_id)
    2. Parse MIME content
    3. Store raw email in S3 (vqms-email-raw-prod)
    4. Store attachments in S3 (vqms-email-attachments-prod)
    5. Persist metadata in PostgreSQL (intake.email_messages)
    6. Publish EmailReceived event to EventBridge
    7. Send message to email-intake SQS queue

    Args:
        raw_email: Raw email data from Graph API.
        redis_client: Async Redis client for idempotency checks.
        db_pool: asyncpg connection pool for metadata persistence.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        EmailIntakeResult with persisted records and deduplication flag.

    Raises:
        EmailIntakeError: When any ingestion step fails.
    """
    _ = db_pool  # reserved for Phase 2 PostgreSQL persistence
    cid = ensure_correlation_id(correlation_id)
    message_id = str(raw_email.get("id", ""))

    try:
        # Step 1: Idempotency check via Redis
        if redis_client is not None:
            idem_key = idempotency_key(message_id)
            existing = await redis_client.get(idem_key)
            if existing is not None:
                logger.info(
                    "email_duplicate_skipped",
                    extra={
                        "message_id": message_id,
                        "correlation_id": cid,
                    },
                )
                # Return early with a minimal result
                parsed = await parse_email(
                    raw_email, correlation_id=cid,
                )
                return EmailIntakeResult(
                    email_message=_build_email_message(
                        raw_email, s3_key="", correlation_id=cid,
                    ),
                    parsed_payload=parsed,
                    is_duplicate=True,
                    s3_raw_key="",
                )

        # Step 2: Parse email content
        parsed = await parse_email(
            raw_email, correlation_id=cid,
        )

        # Step 3: Store raw email in S3
        now = utc_now()
        s3_raw_key = (
            f"{now.year}/{now.month:02d}/"
            f"{now.day:02d}/{message_id}.eml"
        )
        raw_bytes = _json.dumps(
            raw_email, default=str,
        ).encode("utf-8")
        await upload_object(
            VQMSBucket.EMAIL_RAW,
            s3_raw_key,
            raw_bytes,
            content_type="message/rfc822",
            correlation_id=cid,
        )

        # Step 4: Store attachments in S3
        raw_attachments: Any = raw_email.get("attachments", [])
        attachment_models: list[EmailAttachment] = []
        if isinstance(raw_attachments, list):
            for att in raw_attachments:
                att_id = str(att.get("id", ""))
                att_name = str(att.get("name", "unknown"))
                att_content_type = str(
                    att.get("contentType", "application/octet-stream"),
                )
                att_bytes_str = str(att.get("contentBytes", ""))
                att_data = base64.b64decode(att_bytes_str)
                att_s3_key = f"{message_id}/{att_id}"
                await upload_object(
                    VQMSBucket.EMAIL_ATTACHMENTS,
                    att_s3_key,
                    att_data,
                    content_type=att_content_type,
                    correlation_id=cid,
                )
                checksum = hashlib.sha256(att_data).hexdigest()
                attachment_models.append(
                    EmailAttachment(
                        attachment_id=att_id,
                        email_message_id=message_id,
                        filename=att_name,
                        content_type=att_content_type,
                        size_bytes=len(att_data),
                        s3_key=att_s3_key,
                        checksum_sha256=checksum,
                    ),
                )

        # Step 5: Build email message model
        email_msg = _build_email_message(
            raw_email,
            s3_key=s3_raw_key,
            correlation_id=cid,
            attachments=attachment_models,
        )

        # Step 6: Set Redis idempotency key (24h TTL)
        if redis_client is not None:
            await redis_client.set(
                idempotency_key(message_id),
                message_id,
                ex=86400,
            )

        # Step 7: Publish EmailReceived event
        await eb_publish(
            VQMSEventType.EMAIL_RECEIVED,
            detail={
                "email_message_id": message_id,
                "sender_email": email_msg.sender_email,
                "subject": email_msg.subject,
            },
            correlation_id=cid,
        )

        # Step 8: Send to SQS intake queue
        await sqs_send(
            VQMSQueue.EMAIL_INTAKE,
            body={
                "email_message_id": message_id,
                "correlation_id": cid,
                "timestamp": utc_now().isoformat(),
            },
            message_group_id=email_msg.conversation_id,
            correlation_id=cid,
        )

        logger.info(
            "email_ingested",
            extra={
                "message_id": message_id,
                "s3_raw_key": s3_raw_key,
                "attachment_count": len(attachment_models),
                "correlation_id": cid,
            },
        )
        return EmailIntakeResult(
            email_message=email_msg,
            parsed_payload=parsed,
            is_duplicate=False,
            s3_raw_key=s3_raw_key,
        )
    except EmailIntakeError:
        raise
    except Exception as exc:
        msg = f"Email ingestion failed for {message_id}: {exc}"
        raise EmailIntakeError(msg) from exc


def _build_email_message(
    raw_email: dict[str, object],
    *,
    s3_key: str,
    correlation_id: str,
    attachments: list[EmailAttachment] | None = None,
) -> EmailMessage:
    """Build an EmailMessage model from raw Graph API data."""
    from_obj: Any = raw_email.get("from", {})
    email_addr_obj: Any = from_obj.get("emailAddress", {})
    sender_email = str(
        email_addr_obj.get("address", "unknown@unknown.com"),
    )
    sender_name = str(email_addr_obj.get("name", ""))

    to_list: Any = raw_email.get("toRecipients", [])
    recipients: list[str] = []
    if isinstance(to_list, list):
        for r in to_list:
            r_addr: Any = r.get("emailAddress", {})
            recipients.append(
                str(r_addr.get("address", "")),
            )

    received_str = str(
        raw_email.get("receivedDateTime", ""),
    )
    try:
        received_at = datetime.fromisoformat(
            received_str.replace("Z", "+00:00"),
        )
    except (ValueError, TypeError):
        received_at = datetime.now(UTC)

    return EmailMessage(
        message_id=str(raw_email.get("id", "")),
        internet_message_id=str(
            raw_email.get("internetMessageId", ""),
        ),
        conversation_id=str(
            raw_email.get("conversationId", ""),
        ),
        subject=str(raw_email.get("subject", "")),
        sender_email=sender_email,
        sender_name=sender_name,
        recipients=recipients,
        received_at=received_at,
        direction=EmailDirection.INBOUND,
        s3_raw_key=s3_key,
        has_attachments=bool(raw_email.get("hasAttachments")),
        attachments=attachments or [],
        correlation_id=correlation_id,
    )
