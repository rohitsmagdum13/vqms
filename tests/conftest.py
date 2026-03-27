"""Shared test fixtures and mock LLM stubs for the VQMS test suite.

Provides reusable fixtures for database connections, Redis clients,
mock Bedrock responses, sample email payloads, and correlation IDs.
All fixtures follow pytest-asyncio patterns.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

# Moto requires dummy AWS credentials to be set
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")


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


@pytest.fixture
def sample_ticket_record() -> dict[str, object]:
    """Provide a sample ticket record for testing."""
    now = datetime.now(UTC)
    return {
        "ticket_number": "INC0012345",
        "sys_id": "abc123def456",
        "status": "new",
        "priority": "medium",
        "short_description": "Invoice query for PO#12345",
        "email_message_id": "AAMkAGI2TG93AAA=",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "sla_breach_at": (now + timedelta(hours=24)).isoformat(),
        "correlation_id": "test-correlation-00000000-0000-0000-0000-000000000000",
    }


@pytest.fixture
def sample_analysis_result() -> dict[str, object]:
    """Provide a sample email analysis result for testing."""
    return {
        "email_message_id": "AAMkAGI2TG93AAA=",
        "intent": "inquiry",
        "entities": {"vendor_name": ["Test Vendor Corp"], "po_number": ["PO#12345"]},
        "urgency": "medium",
        "sentiment": "neutral",
        "confidence": 0.92,
        "is_multi_issue": False,
        "is_reply": False,
        "summary": "Vendor inquiring about invoice status for PO#12345",
        "correlation_id": "test-correlation-00000000-0000-0000-0000-000000000000",
    }


@pytest.fixture
def sample_budget() -> dict[str, object]:
    """Provide a sample budget configuration for testing."""
    return {
        "max_tokens_in": 8192,
        "max_tokens_out": 4096,
        "currency_limit": 0.50,
        "max_hops": 4,
    }


@pytest.fixture
def sample_agent_message() -> dict[str, object]:
    """Provide a sample agent message envelope for testing."""
    return {
        "id": "msg-001",
        "role": "worker",
        "content": "Analysis complete for email AAMkAGI2TG93AAA=",
        "correlation_id": "test-correlation-00000000-0000-0000-0000-000000000000",
        "timestamp": datetime.now(UTC).isoformat(),
    }
