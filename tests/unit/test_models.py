"""Unit tests for VQMS Pydantic domain models.

Tests schema validation, field constraints, default values,
and serialization for all models in src/models/.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.budget import Budget, BudgetUsage
from src.models.communication import (
    DraftEmailPackage,
    DraftType,
    ValidationReport,
    ValidationStatus,
)
from src.models.email import (
    EmailAttachment,
    EmailDirection,
    EmailMessage,
    ParsedEmailPayload,
)
from src.models.memory import EmbeddingRecord, EpisodicMemory, VendorProfileCache
from src.models.messages import AgentMessage, ToolCall
from src.models.ticket import (
    RoutingDecision,
    RoutingPath,
    TicketLink,
    TicketRecord,
    TicketStatus,
)
from src.models.vendor import VendorMatch, VendorProfile, VendorTier
from src.models.workflow import (
    AnalysisResult,
    CaseExecution,
    IntentType,
    SentimentType,
    UrgencyLevel,
    WorkflowState,
    WorkflowStatus,
)


class TestEmailModels:
    """Tests for email domain models."""

    def test_email_message_valid(self, sample_email_message: dict) -> None:
        msg = EmailMessage(**sample_email_message)
        assert msg.message_id == "AAMkAGI2TG93AAA="
        assert msg.sender_email == "vendor@example.com"
        assert msg.direction == EmailDirection.INBOUND

    def test_email_message_sender_email_normalized(self) -> None:
        msg = EmailMessage(
            message_id="test-id",
            internet_message_id="<test@ex.com>",
            conversation_id="conv-1",
            subject="Test",
            sender_email="  Vendor@Example.COM  ",
            received_at=datetime.now(UTC),
            s3_raw_key="raw/test.eml",
            correlation_id="cid-1",
        )
        assert msg.sender_email == "vendor@example.com"

    def test_email_message_invalid_sender_email(self) -> None:
        with pytest.raises(ValidationError, match="Invalid sender email"):
            EmailMessage(
                message_id="test-id",
                internet_message_id="<test@ex.com>",
                conversation_id="conv-1",
                subject="Test",
                sender_email="not-an-email",
                received_at=datetime.now(UTC),
                s3_raw_key="raw/test.eml",
                correlation_id="cid-1",
            )

    def test_email_message_has_attachments_auto_sync(self) -> None:
        attachment = EmailAttachment(
            attachment_id="att-1",
            email_message_id="msg-1",
            filename="invoice.pdf",
            content_type="application/pdf",
            size_bytes=1024,
            s3_key="attachments/invoice.pdf",
            checksum_sha256="abc123",
        )
        msg = EmailMessage(
            message_id="msg-1",
            internet_message_id="<test@ex.com>",
            conversation_id="conv-1",
            subject="Test",
            sender_email="vendor@example.com",
            received_at=datetime.now(UTC),
            s3_raw_key="raw/test.eml",
            has_attachments=False,
            attachments=[attachment],
            correlation_id="cid-1",
        )
        assert msg.has_attachments is True

    def test_email_attachment_size_bytes_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            EmailAttachment(
                attachment_id="att-1",
                email_message_id="msg-1",
                filename="test.txt",
                content_type="text/plain",
                size_bytes=-1,
                s3_key="attachments/test.txt",
                checksum_sha256="abc",
            )

    def test_parsed_email_payload_valid(self) -> None:
        payload = ParsedEmailPayload(
            message_id="msg-1",
            plain_text_body="Hello, I have an invoice query.",
            correlation_id="cid-1",
        )
        assert payload.is_reply is False
        assert payload.html_body is None
        assert payload.references == []


class TestVendorModels:
    """Tests for vendor domain models."""

    def test_vendor_profile_valid(self, sample_vendor_profile: dict) -> None:
        profile = VendorProfile(**sample_vendor_profile)
        assert profile.vendor_name == "Test Vendor Corp"
        assert profile.tier == VendorTier.GOLD

    def test_vendor_profile_email_normalized(self) -> None:
        profile = VendorProfile(
            vendor_id="001ABC123DEF456",
            vendor_name="Test Corp",
            contact_email="  VENDOR@Example.COM  ",
        )
        assert profile.contact_email == "vendor@example.com"

    def test_vendor_profile_invalid_email(self) -> None:
        with pytest.raises(ValidationError, match="Invalid contact email"):
            VendorProfile(
                vendor_id="001ABC123DEF456",
                vendor_name="Test Corp",
                contact_email="no-at-sign",
            )

    def test_vendor_profile_defaults(self) -> None:
        profile = VendorProfile(
            vendor_id="001ABC123DEF456",
            vendor_name="Test Corp",
            contact_email="v@example.com",
        )
        assert profile.tier == VendorTier.UNCLASSIFIED
        assert profile.sla_response_hours == 24
        assert profile.active is True

    def test_vendor_profile_sla_hours_minimum(self) -> None:
        with pytest.raises(ValidationError):
            VendorProfile(
                vendor_id="001ABC123DEF456",
                vendor_name="Test Corp",
                contact_email="v@example.com",
                sla_response_hours=0,
            )

    def test_vendor_match_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            VendorMatch(confidence=1.5, correlation_id="cid-1")

    def test_vendor_match_defaults(self) -> None:
        match = VendorMatch(correlation_id="cid-1")
        assert match.resolved is False
        assert match.confidence == 0.0
        assert match.match_method == "none"


class TestTicketModels:
    """Tests for ticket domain models."""

    def test_ticket_record_valid(self, sample_ticket_record: dict) -> None:
        ticket = TicketRecord(**sample_ticket_record)
        assert ticket.ticket_number == "INC0012345"
        assert ticket.status == TicketStatus.NEW

    def test_ticket_record_invalid_number(self) -> None:
        with pytest.raises(ValidationError, match="Invalid ticket number"):
            TicketRecord(
                ticket_number="INVALID123",
                sys_id="abc",
                short_description="test",
                email_message_id="msg-1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                correlation_id="cid-1",
            )

    def test_ticket_record_valid_number_formats(self) -> None:
        for num in ["INC0000001", "INC0012345", "INC1234567890"]:
            ticket = TicketRecord(
                ticket_number=num,
                sys_id="abc",
                short_description="test",
                email_message_id="msg-1",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                correlation_id="cid-1",
            )
            assert ticket.ticket_number == num

    def test_ticket_link_valid(self) -> None:
        link = TicketLink(
            link_id="link-1",
            email_message_id="msg-1",
            ticket_number="INC0012345",
            link_type="created",
            created_at=datetime.now(UTC),
        )
        assert link.link_type == "created"

    def test_routing_decision_valid(self) -> None:
        decision = RoutingDecision(
            decision_id="dec-1",
            email_message_id="msg-1",
            routing_path=RoutingPath.FULL_AUTO,
            confidence=0.95,
            reasoning="High confidence, known vendor",
            decided_at=datetime.now(UTC),
            correlation_id="cid-1",
        )
        assert decision.escalation_level == 0

    def test_routing_decision_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            RoutingDecision(
                decision_id="dec-1",
                email_message_id="msg-1",
                routing_path=RoutingPath.FULL_AUTO,
                confidence=-0.1,
                reasoning="test",
                decided_at=datetime.now(UTC),
                correlation_id="cid-1",
            )


class TestWorkflowModels:
    """Tests for workflow domain models."""

    def test_analysis_result_valid(self, sample_analysis_result: dict) -> None:
        result = AnalysisResult(**sample_analysis_result)
        assert result.intent == IntentType.INQUIRY
        assert result.confidence == 0.92

    def test_analysis_result_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisResult(
                email_message_id="msg-1",
                intent=IntentType.INQUIRY,
                urgency=UrgencyLevel.MEDIUM,
                sentiment=SentimentType.NEUTRAL,
                confidence=1.5,
                summary="test",
                correlation_id="cid-1",
            )

    def test_case_execution_hop_count_max(self) -> None:
        with pytest.raises(ValidationError):
            CaseExecution(
                case_id="case-1",
                email_message_id="msg-1",
                started_at=datetime.now(UTC),
                hop_count=5,
                correlation_id="cid-1",
            )

    def test_case_execution_defaults(self) -> None:
        case = CaseExecution(
            case_id="case-1",
            email_message_id="msg-1",
            started_at=datetime.now(UTC),
            correlation_id="cid-1",
        )
        assert case.status == WorkflowStatus.PENDING
        assert case.current_step == "intake"
        assert case.hop_count == 0

    def test_workflow_state_valid(self) -> None:
        case = CaseExecution(
            case_id="case-1",
            email_message_id="msg-1",
            started_at=datetime.now(UTC),
            correlation_id="cid-1",
        )
        state = WorkflowState(case_execution=case)
        assert state.budget_remaining == 0.50
        assert state.messages == []


class TestCommunicationModels:
    """Tests for communication domain models."""

    def test_draft_email_package_valid(self) -> None:
        draft = DraftEmailPackage(
            draft_id="draft-1",
            draft_type=DraftType.ACKNOWLEDGMENT,
            ticket_number="INC0012345",
            vendor_name="Test Corp",
            subject="[INC0012345] Acknowledgment",
            body_html="<p>Thank you</p>",
            body_plain="Thank you",
            sla_statement="We will respond within 24 hours",
            created_at=datetime.now(UTC),
            model_id="anthropic.claude-3-5-sonnet",
            prompt_version="v1",
            correlation_id="cid-1",
        )
        assert draft.tokens_used == 0

    def test_draft_email_package_invalid_ticket(self) -> None:
        with pytest.raises(ValidationError, match="Invalid ticket number"):
            DraftEmailPackage(
                draft_id="draft-1",
                draft_type=DraftType.ACKNOWLEDGMENT,
                ticket_number="BAD-NUMBER",
                vendor_name="Test Corp",
                subject="Test",
                body_html="<p>Test</p>",
                body_plain="Test",
                sla_statement="24h",
                created_at=datetime.now(UTC),
                model_id="claude",
                prompt_version="v1",
                correlation_id="cid-1",
            )

    def test_validation_report_valid(self) -> None:
        report = ValidationReport(
            report_id="rpt-1",
            draft_id="draft-1",
            status=ValidationStatus.PASSED,
            ticket_number_valid=True,
            sla_wording_valid=True,
            template_compliant=True,
            governance_policy_met=True,
            validated_at=datetime.now(UTC),
            correlation_id="cid-1",
        )
        assert report.pii_detected is False


class TestMemoryModels:
    """Tests for memory domain models."""

    def test_episodic_memory_valid(self) -> None:
        now = datetime.now(UTC)
        mem = EpisodicMemory(
            memory_id="mem-1",
            vendor_id="001ABC123DEF456",
            case_id="case-1",
            email_message_id="msg-1",
            intent="inquiry",
            resolution_summary="Resolved via email",
            outcome="resolved",
            tags=["invoice", "po"],
            created_at=now,
            expires_at=now + timedelta(days=180),
            correlation_id="cid-1",
        )
        assert mem.tags == ["invoice", "po"]

    def test_vendor_profile_cache_email_normalized(self) -> None:
        cache = VendorProfileCache(
            vendor_id="001ABC123DEF456",
            vendor_name="Test Corp",
            contact_email="  TEST@Example.COM  ",
            cached_at=datetime.now(UTC),
        )
        assert cache.contact_email == "test@example.com"

    def test_vendor_profile_cache_invalid_email(self) -> None:
        with pytest.raises(ValidationError, match="Invalid contact email"):
            VendorProfileCache(
                vendor_id="001ABC123DEF456",
                vendor_name="Test Corp",
                contact_email="no-at",
                cached_at=datetime.now(UTC),
            )

    def test_embedding_record_valid(self) -> None:
        record = EmbeddingRecord(
            embedding_id="emb-1",
            source_type="email",
            source_id="msg-1",
            chunk_id="chunk-0",
            content="Test content for embedding",
            embedding=[0.1] * 1024,
            created_at=datetime.now(UTC),
        )
        assert len(record.embedding) == 1024

    def test_embedding_record_empty_vector_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            EmbeddingRecord(
                embedding_id="emb-1",
                source_type="email",
                source_id="msg-1",
                chunk_id="chunk-0",
                content="Test",
                embedding=[],
                created_at=datetime.now(UTC),
            )


class TestBudgetModels:
    """Tests for budget domain models."""

    def test_budget_defaults(self) -> None:
        budget = Budget()
        assert budget.max_tokens_in == 8192
        assert budget.max_tokens_out == 4096
        assert budget.currency_limit == 0.50
        assert budget.max_hops == 4
        assert budget.deadline is None

    def test_budget_immutable(self) -> None:
        budget = Budget()
        with pytest.raises(AttributeError):
            budget.max_tokens_in = 999  # type: ignore[misc]

    def test_budget_usage_mutable(self) -> None:
        usage = BudgetUsage()
        usage.tokens_in = 100
        usage.hop_count = 2
        assert usage.tokens_in == 100
        assert usage.cost_usd == 0.0

    def test_budget_with_deadline(self) -> None:
        deadline = datetime.now(UTC) + timedelta(hours=1)
        budget = Budget(deadline=deadline)
        assert budget.deadline == deadline


class TestMessageModels:
    """Tests for inter-agent message models."""

    def test_agent_message_valid(self, sample_agent_message: dict) -> None:
        msg = AgentMessage(**sample_agent_message)
        assert msg.role == "worker"
        assert msg.parent_id is None

    def test_agent_message_invalid_role(self) -> None:
        with pytest.raises(ValidationError):
            AgentMessage(
                id="msg-1",
                role="invalid_role",
                content="test",
                correlation_id="cid-1",
                timestamp=datetime.now(UTC),
            )

    def test_agent_message_with_tool_calls(self) -> None:
        tool = ToolCall(name="search_email", args={"query": "PO#12345"})
        msg = AgentMessage(
            id="msg-1",
            role="worker",
            content="Searching for email",
            tool_calls=[tool],
            correlation_id="cid-1",
            timestamp=datetime.now(UTC),
        )
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "search_email"

    def test_tool_call_defaults(self) -> None:
        tool = ToolCall(name="fetch_vendor")
        assert tool.args == {}
