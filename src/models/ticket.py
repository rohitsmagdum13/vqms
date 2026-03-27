"""Module: ticket
Description: Pydantic models for ticket operations in the VQMS pipeline.

Defines TicketRecord, TicketLink, and RoutingDecision models used by the
Ticket Operations Service (Step 8) and Workflow Orchestration Agent (Step 6).
Maps to workflow.ticket_link and workflow.routing_decision PostgreSQL tables.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TicketStatus(StrEnum):
    """ServiceNow ticket status values."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    AWAITING_INFO = "awaiting_info"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class TicketPriority(StrEnum):
    """Ticket priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RoutingPath(StrEnum):
    """Routing paths determined by the Orchestration Agent."""

    FULL_AUTO = "full_auto"
    LOW_CONFIDENCE = "low_confidence"
    EXISTING_TICKET = "existing_ticket"
    REOPEN = "reopen"
    ESCALATION = "escalation"


class TicketRecord(BaseModel):
    """Represents a ServiceNow ticket record.

    Created or updated by the Ticket Operations Service (Step 8).
    Idempotency enforced via check-before-create pattern.

    Attributes:
        ticket_number: ServiceNow ticket number (e.g., INC0012345).
        sys_id: ServiceNow internal system ID.
        status: Current ticket status.
        priority: Ticket priority level.
        short_description: Brief description of the issue.
        description: Full ticket description.
        assigned_to: Assigned agent or group.
        vendor_id: Associated vendor Salesforce ID.
        email_message_id: Originating email message ID.
        created_at: Ticket creation timestamp.
        updated_at: Last update timestamp.
        sla_breach_at: Timestamp when SLA breaches.
        correlation_id: Tracing ID propagated through the pipeline.
    """

    ticket_number: str = Field(..., description="ServiceNow ticket number")
    sys_id: str = Field(..., description="ServiceNow system ID")
    status: TicketStatus = Field(default=TicketStatus.NEW, description="Ticket status")
    priority: TicketPriority = Field(
        default=TicketPriority.MEDIUM, description="Priority level"
    )
    short_description: str = Field(..., description="Brief issue description")
    description: str = Field(default="", description="Full ticket description")
    assigned_to: str = Field(default="", description="Assigned agent or group")
    vendor_id: str = Field(default="", description="Vendor Salesforce Account ID")
    email_message_id: str = Field(..., description="Originating email message ID")
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    sla_breach_at: datetime | None = Field(
        default=None, description="SLA breach timestamp"
    )
    correlation_id: str = Field(..., description="Pipeline correlation ID")


class TicketLink(BaseModel):
    """Links an email message to a ServiceNow ticket.

    Maps to workflow.ticket_link table for tracking email-to-ticket
    associations and thread correlation.

    Attributes:
        link_id: Unique identifier for the link.
        email_message_id: Email message identifier.
        ticket_number: ServiceNow ticket number.
        link_type: Type of association (created, updated, reopened).
        created_at: Link creation timestamp.
    """

    link_id: str = Field(..., description="Unique link identifier")
    email_message_id: str = Field(..., description="Email message ID")
    ticket_number: str = Field(..., description="ServiceNow ticket number")
    link_type: str = Field(
        ..., description="Association type: created, updated, reopened"
    )
    created_at: datetime = Field(..., description="Link creation timestamp")


class RoutingDecision(BaseModel):
    """Routing decision made by the Workflow Orchestration Agent.

    Maps to workflow.routing_decision table. Determines which path
    the email takes through the VQMS pipeline.

    Attributes:
        decision_id: Unique decision identifier.
        email_message_id: Email being routed.
        routing_path: Selected routing path.
        confidence: Decision confidence score.
        reasoning: Explanation of the routing decision.
        vendor_id: Resolved vendor ID (if applicable).
        existing_ticket_number: Existing ticket (if found).
        escalation_level: Escalation level (0=none, 1=L1, 2=L2).
        decided_at: Decision timestamp.
        correlation_id: Tracing ID propagated through the pipeline.
    """

    decision_id: str = Field(..., description="Unique decision identifier")
    email_message_id: str = Field(..., description="Email being routed")
    routing_path: RoutingPath = Field(..., description="Selected routing path")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence")
    reasoning: str = Field(..., description="Routing decision explanation")
    vendor_id: str | None = Field(default=None, description="Resolved vendor ID")
    existing_ticket_number: str | None = Field(
        default=None, description="Existing ticket number"
    )
    escalation_level: int = Field(
        default=0, ge=0, le=2, description="Escalation level (0=none, 1=L1, 2=L2)"
    )
    decided_at: datetime = Field(..., description="Decision timestamp")
    correlation_id: str = Field(..., description="Pipeline correlation ID")
