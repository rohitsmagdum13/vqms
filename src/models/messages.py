"""Module: messages
Description: Inter-agent communication envelope models for the VQMS pipeline.

Implements the AgentMessage and ToolCall schemas from Coding Standards
Section 2.1. All inter-agent communication uses these envelope models
to ensure consistent contract enforcement and observability.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    """Represents a tool invocation within the VQMS pipeline.

    Used inside AgentMessage to record which tools were called
    with what arguments during agent execution.

    Attributes:
        name: Name of the tool being invoked.
        args: Tool input arguments as a dictionary.
    """

    name: str = Field(..., description="Tool name")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class AgentMessage(BaseModel):
    """Standard envelope for all inter-agent communication in VQMS.

    Every message passed between agents, orchestrators, and services
    must be wrapped in this envelope to ensure consistent contract
    enforcement, tracing, and observability.

    Attributes:
        id: Unique message identifier.
        parent_id: ID of the parent message (for threading).
        role: Role of the message sender.
        content: Message content (string or structured dict).
        tool_calls: List of tool invocations in this message.
        annotations: Metadata annotations (cost, tokens, safety flags).
        correlation_id: Tracing ID propagated through the pipeline.
        timestamp: Message creation timestamp.
    """

    id: str = Field(..., description="Unique message identifier")
    parent_id: str | None = Field(
        default=None, description="Parent message ID for threading"
    )
    role: Literal["system", "planner", "worker", "reviewer", "user"] = Field(
        ..., description="Sender role"
    )
    content: str | dict[str, Any] = Field(..., description="Message content")
    tool_calls: list[ToolCall] = Field(
        default_factory=list, description="Tool invocations"
    )
    annotations: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata: cost, tokens, safety flags",
    )
    correlation_id: str = Field(..., description="Pipeline correlation ID")
    timestamp: datetime = Field(..., description="Message creation timestamp")
