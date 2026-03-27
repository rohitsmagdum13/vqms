"""Module: workflow
Description: Pydantic models for workflow state management in the VQMS pipeline.

Defines WorkflowState, CaseExecution, and AnalysisResult models used by
the orchestration layer (LangGraph + Step Functions). Maps to
workflow.case_execution PostgreSQL table.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WorkflowStatus(StrEnum):
    """Workflow execution status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class IntentType(StrEnum):
    """Email intent classification types."""

    INQUIRY = "inquiry"
    COMPLAINT = "complaint"
    REQUEST = "request"
    FOLLOW_UP = "follow_up"
    ESCALATION = "escalation"
    RESOLUTION = "resolution"


class UrgencyLevel(StrEnum):
    """Urgency levels for email classification."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SentimentType(StrEnum):
    """Sentiment classification for email analysis."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ESCALATING = "escalating"


class AnalysisResult(BaseModel):
    """Result of email analysis by the Email Analysis Agent (Step 5A).

    Contains structured extraction of intent, entities, urgency,
    sentiment, and confidence scoring from the incoming vendor email.

    Attributes:
        email_message_id: Reference to the analyzed email.
        intent: Classified email intent.
        entities: Extracted entities (vendor name, ticket refs, dates, etc.).
        urgency: Assessed urgency level.
        sentiment: Detected sentiment.
        confidence: Overall analysis confidence score.
        is_multi_issue: Whether multiple issues were detected.
        is_reply: Whether the email is a reply to an existing thread.
        summary: Brief summary of the email content.
        raw_analysis: Full LLM response for audit trail.
        correlation_id: Tracing ID propagated through the pipeline.
    """

    email_message_id: str = Field(..., description="Analyzed email message ID")
    intent: IntentType = Field(..., description="Classified email intent")
    entities: dict[str, list[str]] = Field(
        default_factory=dict, description="Extracted entities by category"
    )
    urgency: UrgencyLevel = Field(..., description="Assessed urgency level")
    sentiment: SentimentType = Field(..., description="Detected sentiment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    is_multi_issue: bool = Field(
        default=False, description="Multiple issues detected flag"
    )
    is_reply: bool = Field(default=False, description="Reply to existing thread flag")
    summary: str = Field(..., description="Brief email content summary")
    raw_analysis: dict[str, object] = Field(
        default_factory=dict, description="Full LLM response for audit"
    )
    correlation_id: str = Field(..., description="Pipeline correlation ID")


class CaseExecution(BaseModel):
    """Represents a single workflow case execution in the VQMS pipeline.

    Maps to workflow.case_execution table. Tracks the full lifecycle
    of processing a vendor email from ingestion to resolution.

    Attributes:
        case_id: Unique case execution identifier.
        email_message_id: Originating email message ID.
        status: Current workflow status.
        current_step: Name of the current pipeline step.
        step_history: Ordered list of completed steps.
        analysis_result: Email analysis output (populated after Step 5A).
        vendor_id: Resolved vendor ID (populated after Step 5B).
        ticket_number: Created/updated ticket (populated after Step 8).
        routing_path: Selected routing path (populated after Step 6).
        started_at: Workflow start timestamp.
        completed_at: Workflow completion timestamp.
        error_message: Error details if workflow failed.
        hop_count: Number of agent hops consumed (max 4).
        correlation_id: Tracing ID propagated through the pipeline.
    """

    case_id: str = Field(..., description="Unique case execution ID")
    email_message_id: str = Field(..., description="Originating email message ID")
    status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING, description="Workflow status"
    )
    current_step: str = Field(default="intake", description="Current pipeline step")
    step_history: list[str] = Field(
        default_factory=list, description="Completed steps in order"
    )
    analysis_result: AnalysisResult | None = Field(
        default=None, description="Email analysis output"
    )
    vendor_id: str | None = Field(default=None, description="Resolved vendor ID")
    ticket_number: str | None = Field(
        default=None, description="Created/updated ticket number"
    )
    routing_path: str | None = Field(
        default=None, description="Selected routing path"
    )
    started_at: datetime = Field(..., description="Workflow start timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Workflow completion timestamp"
    )
    error_message: str | None = Field(
        default=None, description="Error details if failed"
    )
    hop_count: int = Field(default=0, ge=0, le=4, description="Agent hop count")
    correlation_id: str = Field(..., description="Pipeline correlation ID")


class WorkflowState(BaseModel):
    """LangGraph state object passed between nodes in the orchestration graph.

    This is the in-graph agent state (tier 4 of the four-tier memory system).
    Carries all context needed for routing decisions.

    Attributes:
        case_execution: Current case execution record.
        email_payload: Parsed email content.
        vendor_match: Vendor resolution result.
        existing_tickets: List of existing tickets for this thread.
        policy_context: Applicable governance policies.
        budget_remaining: Remaining budget for this execution.
        messages: Agent message history for this workflow run.
    """

    case_execution: CaseExecution = Field(..., description="Current case execution")
    email_payload: dict[str, object] = Field(
        default_factory=dict, description="Parsed email content"
    )
    vendor_match: dict[str, object] | None = Field(
        default=None, description="Vendor resolution result"
    )
    existing_tickets: list[dict[str, object]] = Field(
        default_factory=list, description="Existing tickets for this thread"
    )
    policy_context: dict[str, object] = Field(
        default_factory=dict, description="Applicable governance policies"
    )
    budget_remaining: float = Field(
        default=0.50, ge=0.0, description="Remaining budget in currency"
    )
    messages: list[dict[str, object]] = Field(
        default_factory=list, description="Agent message history"
    )
