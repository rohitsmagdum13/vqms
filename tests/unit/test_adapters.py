"""Unit tests for external system adapters (contract tests).

Tests adapter I/O contracts with strict pydantic model validation
per Coding Standards Section 8.1.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.adapters.graph_api import (
    GraphAPIConfig,
    GraphAPIError,
    fetch_messages,
    mark_as_read,
    send_message,
)


def _graph_config() -> GraphAPIConfig:
    return GraphAPIConfig(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
        access_token="test-token",
        mailbox_id="user@example.com",
        timeout_seconds=5,
    )


def _mock_response(
    *,
    status_code: int = 200,
    json_data: dict | None = None,
) -> httpx.Response:
    """Build a fake httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", "https://test"),
    )


class TestGraphAPIAdapter:
    """Contract tests for Microsoft Graph API adapter."""

    @pytest.mark.asyncio
    async def test_fetch_messages_returns_list(self) -> None:
        mock_resp = _mock_response(
            json_data={
                "value": [
                    {"id": "msg-1", "subject": "Test"},
                    {"id": "msg-2", "subject": "Test 2"},
                ],
            },
        )
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await fetch_messages(
                _graph_config(),
                max_results=10,
                correlation_id="test-cid",
            )
        assert len(result) == 2
        assert result[0]["id"] == "msg-1"

    @pytest.mark.asyncio
    async def test_fetch_messages_empty(self) -> None:
        mock_resp = _mock_response(json_data={"value": []})
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await fetch_messages(_graph_config())
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_messages_http_error_raises(self) -> None:
        mock_resp = _mock_response(
            status_code=401,
            json_data={"error": "unauthorized"},
        )
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(GraphAPIError, match="401"):
                await fetch_messages(_graph_config())

    @pytest.mark.asyncio
    async def test_send_message_returns_id(self) -> None:
        mock_resp = _mock_response(status_code=202)
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await send_message(
                _graph_config(),
                to_recipients=["vendor@example.com"],
                subject="Re: Your query",
                body_html="<p>Thank you</p>",
                correlation_id="test-cid",
            )
        assert result == "test-cid"

    @pytest.mark.asyncio
    async def test_send_message_with_threading(self) -> None:
        mock_resp = _mock_response(status_code=202)
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await send_message(
                _graph_config(),
                to_recipients=["vendor@example.com"],
                subject="Re: Thread",
                body_html="<p>Reply</p>",
                in_reply_to="<original@example.com>",
                references=["<original@example.com>"],
                correlation_id="cid",
            )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self) -> None:
        mock_resp = _mock_response(status_code=200)
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.patch = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            # Should not raise
            await mark_as_read(
                _graph_config(),
                "msg-001",
                correlation_id="test-cid",
            )

    @pytest.mark.asyncio
    async def test_mark_as_read_error_raises(self) -> None:
        mock_resp = _mock_response(
            status_code=404,
            json_data={"error": "not found"},
        )
        with patch(
            "src.adapters.graph_api.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.patch = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(
                return_value=mock_client,
            )
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(GraphAPIError, match="404"):
                await mark_as_read(
                    _graph_config(), "msg-nonexistent",
                )


class TestSalesforceAdapter:
    """Contract tests for Salesforce CRM adapter."""

    def test_placeholder(self) -> None:
        """Placeholder test — to be implemented in Phase 6."""
        raise NotImplementedError("Pending implementation")


class TestServiceNowAdapter:
    """Contract tests for ServiceNow ITSM adapter."""

    def test_placeholder(self) -> None:
        """Placeholder test — to be implemented in Phase 6."""
        raise NotImplementedError("Pending implementation")


class TestBedrockAdapter:
    """Contract tests for Bedrock Integration Service adapter."""

    def test_placeholder(self) -> None:
        """Placeholder test — to be implemented in Phase 5."""
        raise NotImplementedError("Pending implementation")
