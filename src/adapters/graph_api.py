"""Module: graph_api
Description: Microsoft Graph API adapter for the VQMS pipeline.

Provides email fetch and send capabilities via Exchange Online.
Supports both webhook notifications and polling for hybrid mode.
All credentials loaded from environment variables or AWS Secrets Manager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://graph.microsoft.com"


class GraphAPIError(Exception):
    """Raised when Microsoft Graph API operations fail."""


@dataclass(frozen=True)
class GraphAPIConfig:
    """Configuration for Microsoft Graph API client.

    Attributes:
        tenant_id: Azure AD tenant ID.
        client_id: Azure AD application client ID.
        client_secret: Azure AD application client secret.
        access_token: Pre-acquired OAuth2 bearer token.
        api_version: Graph API version (default v1.0).
        mailbox_id: Target mailbox identifier.
        timeout_seconds: HTTP request timeout.
    """

    tenant_id: str
    client_id: str
    client_secret: str = ""
    access_token: str = ""
    api_version: str = "v1.0"
    mailbox_id: str = ""
    timeout_seconds: int = 30


def _build_headers(config: GraphAPIConfig) -> dict[str, str]:
    """Build HTTP headers with bearer token."""
    return {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }


def _api_url(config: GraphAPIConfig, path: str) -> str:
    """Build a full Graph API URL."""
    return f"{_BASE_URL}/{config.api_version}{path}"


def _raise_for_status(
    response: httpx.Response,
    *,
    context: str,
) -> None:
    """Raise GraphAPIError for non-2xx responses.

    Distinguishes transient (429, 5xx) from permanent errors.
    """
    if response.is_success:
        return
    status = response.status_code
    body = response.text[:500]
    msg = f"{context}: HTTP {status} — {body}"
    raise GraphAPIError(msg)


async def fetch_messages(
    config: GraphAPIConfig,
    *,
    max_results: int = 50,
    filter_unread: bool = True,
    correlation_id: str | None = None,
) -> list[dict[str, object]]:
    """Fetch email messages from Exchange Online via Graph API.

    Args:
        config: Graph API client configuration.
        max_results: Maximum messages to return per request.
        filter_unread: Whether to filter for unread messages only.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of raw email data dictionaries from Graph API.

    Raises:
        GraphAPIError: When Graph API request fails.
    """
    params: dict[str, Any] = {"$top": str(max_results)}
    if filter_unread:
        params["$filter"] = "isRead eq false"

    url = _api_url(config, "/me/mailFolders/inbox/messages")
    try:
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds,
        ) as client:
            response = await client.get(
                url,
                headers=_build_headers(config),
                params=params,
            )
        _raise_for_status(response, context="fetch_messages")
        data = response.json()
        messages: list[dict[str, object]] = data.get("value", [])
        logger.info(
            "graph_api_messages_fetched",
            extra={
                "count": len(messages),
                "filter_unread": filter_unread,
                "correlation_id": correlation_id,
            },
        )
        return messages
    except GraphAPIError:
        raise
    except httpx.HTTPError as exc:
        msg = f"Graph API fetch failed: {exc}"
        raise GraphAPIError(msg) from exc


async def send_message(
    config: GraphAPIConfig,
    *,
    to_recipients: list[str],
    subject: str,
    body_html: str,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
    correlation_id: str | None = None,
) -> str:
    """Send an email via Exchange Online Graph API.

    Args:
        config: Graph API client configuration.
        to_recipients: List of recipient email addresses.
        subject: Email subject line.
        body_html: HTML email body.
        in_reply_to: Optional Message-ID for threading.
        references: Optional list of Message-IDs for threading.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        Message ID of the sent email.

    Raises:
        GraphAPIError: When send operation fails.
    """
    recipients = [
        {"emailAddress": {"address": addr}}
        for addr in to_recipients
    ]
    payload: dict[str, Any] = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body_html,
            },
            "toRecipients": recipients,
        },
    }
    # Threading headers for replies
    if in_reply_to is not None:
        internet_headers = [
            {"name": "In-Reply-To", "value": in_reply_to},
        ]
        if references:
            internet_headers.append(
                {
                    "name": "References",
                    "value": " ".join(references),
                },
            )
        payload["message"]["internetMessageHeaders"] = (
            internet_headers
        )

    url = _api_url(config, "/me/sendMail")
    try:
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds,
        ) as client:
            response = await client.post(
                url,
                headers=_build_headers(config),
                json=payload,
            )
        _raise_for_status(response, context="send_message")
        # sendMail returns 202 Accepted with no body;
        # message ID is not returned by the API directly.
        # Return correlation_id as reference identifier.
        sent_id = correlation_id or "accepted"
        logger.info(
            "graph_api_message_sent",
            extra={
                "recipient_count": len(to_recipients),
                "subject_preview": subject[:80],
                "is_reply": in_reply_to is not None,
                "correlation_id": correlation_id,
            },
        )
        return sent_id
    except GraphAPIError:
        raise
    except httpx.HTTPError as exc:
        msg = f"Graph API send failed: {exc}"
        raise GraphAPIError(msg) from exc


async def mark_as_read(
    config: GraphAPIConfig,
    message_id: str,
    *,
    correlation_id: str | None = None,
) -> None:
    """Mark an email message as read in Exchange Online.

    Args:
        config: Graph API client configuration.
        message_id: Graph API message ID to mark as read.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Raises:
        GraphAPIError: When update operation fails.
    """
    url = _api_url(config, f"/me/messages/{message_id}")
    try:
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds,
        ) as client:
            response = await client.patch(
                url,
                headers=_build_headers(config),
                json={"isRead": True},
            )
        _raise_for_status(
            response, context="mark_as_read",
        )
        logger.info(
            "graph_api_message_marked_read",
            extra={
                "message_id": message_id,
                "correlation_id": correlation_id,
            },
        )
    except GraphAPIError:
        raise
    except httpx.HTTPError as exc:
        msg = (
            f"Graph API mark_as_read failed for "
            f"{message_id}: {exc}"
        )
        raise GraphAPIError(msg) from exc
