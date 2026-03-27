"""Shared test fixtures and mock LLM stubs for the VQMS test suite.

Provides reusable fixtures for database connections, Redis clients,
mock Bedrock responses, sample email payloads, and correlation IDs.
All fixtures follow pytest-asyncio patterns.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def correlation_id() -> str:
    """Provide a fixed correlation ID for test tracing."""
    return "test-correlation-00000000-0000-0000-0000-000000000000"


@pytest.fixture
def sample_email_message() -> dict[str, object]:
    """Provide a sample email message payload for testing."""
    return {
        "message_id": "AAMkAGI2TG93AAA=",
        "internet_message_id": "<test@example.com>",
        "conversation_id": "AAQkAGI2TG93AAA=",
        "subject": "Invoice Query - PO#12345",
        "sender_email": "vendor@example.com",
        "sender_name": "Test Vendor",
        "recipients": ["support@hexaware.com"],
        "received_at": "2026-03-26T10:00:00Z",
        "direction": "inbound",
        "s3_raw_key": "raw/2026/03/26/AAMkAGI2TG93AAA=.eml",
        "has_attachments": False,
        "correlation_id": "test-correlation-00000000-0000-0000-0000-000000000000",
    }


@pytest.fixture
def sample_vendor_profile() -> dict[str, object]:
    """Provide a sample vendor profile for testing."""
    return {
        "vendor_id": "001ABC123DEF456",
        "vendor_name": "Test Vendor Corp",
        "contact_email": "vendor@example.com",
        "tier": "gold",
        "sla_response_hours": 8,
        "account_manager": "Jane Smith",
        "active": True,
    }


@pytest.fixture
def mock_bedrock_response() -> dict[str, object]:
    """Provide a mock Bedrock Claude response for testing."""
    return {
        "content": "Mock LLM response content",
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "usage": {
            "input_tokens": 150,
            "output_tokens": 50,
        },
        "stop_reason": "end_turn",
    }
