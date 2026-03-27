"""Module: budget
Description: Budget dataclass for cost and token tracking in the VQMS pipeline.

Implements the Budget pattern from Coding Standards Section 1.2.
Every request carries a budget with max tokens in/out and currency limit,
enforced at the orchestration layer to prevent runaway costs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Budget:
    """Per-request budget enforced at the orchestration layer.

    Tracks token consumption and currency limits across all agents
    and tool calls within a single pipeline execution. Immutable
    to prevent accidental mutation during propagation.

    Attributes:
        max_tokens_in: Maximum input tokens allowed.
        max_tokens_out: Maximum output tokens allowed.
        currency_limit: Maximum spend in USD for this request.
        max_hops: Maximum agent hops before forced termination.
        deadline: Absolute deadline for this request.
    """

    max_tokens_in: int = 8192
    max_tokens_out: int = 4096
    currency_limit: float = 0.50
    max_hops: int = 4
    deadline: datetime | None = None


@dataclass
class BudgetUsage:
    """Tracks cumulative budget consumption during pipeline execution.

    Mutable tracker that accumulates token and cost usage across
    all agent hops and tool calls. Checked against the Budget
    limits at each step by the orchestration layer.

    Attributes:
        tokens_in: Total input tokens consumed so far.
        tokens_out: Total output tokens consumed so far.
        cost_usd: Total cost in USD consumed so far.
        hop_count: Number of agent hops consumed.
        tool_calls: Number of tool calls made.
        model_calls: Per-model call counts for observability.
    """

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    hop_count: int = 0
    tool_calls: int = 0
    model_calls: dict[str, int] = field(default_factory=dict)
