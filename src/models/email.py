"""Module: email
Description: Pydantic models for email ingestion and parsing in the VQMS pipeline.

Defines EmailMessage, EmailAttachment, and ParsedEmailPayload models
corresponding to the intake.email_messages and intake.email_attachments
PostgreSQL tables (Architecture Doc Section 4).
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmailDirection(StrEnum):
    """Direction of email flow."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class EmailAttachment(BaseModel):
    """Represents a file attachment on an email message.

    Maps to intake.email_attachments table. Attachments are stored
    in the vqms-email-attachments-prod S3 bucket.

    Attributes:
        attachment_id: Unique identifier for the attachment.
        email_message_id: Foreign key to the parent email message.
        filename: Original filename of the attachment.
        content_type: MIME content type (e.g., application/pdf).
        size_bytes: Size of the attachment in bytes.
        s3_key: S3 object key in vqms-email-attachments-prod bucket.
        checksum_sha256: SHA-256 hash for integrity verification.
    """

    attachment_id: str = Field(..., description="Unique identifier for the attachment")
    email_message_id: str = Field(..., description="Foreign key to parent email")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., ge=0, description="Size in bytes")
    s3_key: str = Field(..., description="S3 object key in attachments bucket")
    checksum_sha256: str = Field(..., description="SHA-256 hash for integrity")


class EmailMessage(BaseModel):
    """Represents an ingested email message in the VQMS pipeline.

    Maps to intake.email_messages table. Raw email content is stored
    in the vqms-email-raw-prod S3 bucket.

    Attributes:
        message_id: Microsoft Graph API message ID (idempotency key).
        internet_message_id: RFC 2822 Message-ID header.
        conversation_id: Graph API conversation/thread ID.
        subject: Email subject line.
        sender_email: Sender email address.
        sender_name: Sender display name.
        recipients: List of recipient email addresses.
        received_at: Timestamp when the email was received.
        direction: Inbound or outbound email.
        s3_raw_key: S3 key for the raw email in vqms-email-raw-prod.
        has_attachments: Whether the email has attachments.
        attachments: List of attachment metadata.
        correlation_id: Tracing ID propagated through the pipeline.
    """

    message_id: str = Field(..., description="Graph API message ID (idempotency key)")
    internet_message_id: str = Field(..., description="RFC 2822 Message-ID header")
    conversation_id: str = Field(..., description="Graph API conversation/thread ID")
    subject: str = Field(..., description="Email subject line")
    sender_email: str = Field(..., description="Sender email address")
    sender_name: str = Field(default="", description="Sender display name")
    recipients: list[str] = Field(default_factory=list, description="Recipient emails")
    received_at: datetime = Field(..., description="Receive timestamp")
    direction: EmailDirection = Field(
        default=EmailDirection.INBOUND, description="Email direction"
    )
    s3_raw_key: str = Field(..., description="S3 key for raw email content")
    has_attachments: bool = Field(default=False, description="Has attachments flag")
    attachments: list[EmailAttachment] = Field(
        default_factory=list, description="Attachment metadata"
    )
    correlation_id: str = Field(..., description="Pipeline correlation ID")


class ParsedEmailPayload(BaseModel):
    """Structured payload extracted from a raw email after MIME parsing.

    Produced by the Email Ingestion Service (Steps 2-3) and consumed
    by the Email Analysis Agent (Step 5A).

    Attributes:
        message_id: Reference to the parent EmailMessage.
        plain_text_body: Plain text body extracted from MIME.
        html_body: HTML body extracted from MIME (if present).
        headers: Key email headers (In-Reply-To, References, etc.).
        is_reply: Whether this email is a reply to an existing thread.
        in_reply_to: Message-ID of the email being replied to.
        references: List of Message-IDs in the References header chain.
        correlation_id: Tracing ID propagated through the pipeline.
    """

    message_id: str = Field(..., description="Reference to parent EmailMessage")
    plain_text_body: str = Field(..., description="Plain text body from MIME")
    html_body: str | None = Field(default=None, description="HTML body from MIME")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Key email headers"
    )
    is_reply: bool = Field(default=False, description="Whether email is a reply")
    in_reply_to: str | None = Field(
        default=None, description="Message-ID being replied to"
    )
    references: list[str] = Field(
        default_factory=list, description="Message-IDs in References chain"
    )
    correlation_id: str = Field(..., description="Pipeline correlation ID")
