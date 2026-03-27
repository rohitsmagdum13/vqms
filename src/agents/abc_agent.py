"""Module: abc_agent
Description: Abstract base class for all VQMS agents.

Defines the common interface and lifecycle hooks that every agent
in the VQMS pipeline must implement. Enforces single responsibility,
budget tracking, stop conditions, and observability requirements
per Coding Standards Section 4.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.models.budget import Budget, BudgetUsage
from src.models.messages import AgentMessage

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Raised when agent execution fails."""


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for an agent instance.

    Attributes:
        agent_id: Unique agent identifier.
        agent_role: Role name (e.g., email_analysis, communication_drafting).
        model_id: LLM model identifier for this agent.
        prompt_template_path: Path to versioned prompt template.
        max_hops: Maximum number of agent hops allowed.
        temperature: LLM temperature setting.
    """

    agent_id: str
    agent_role: str
    model_id: str
    prompt_template_path: str
    max_hops: int = 4
    temperature: float = 0.1


class BaseAgent(ABC):
    """Abstract base class for all VQMS agents.

    Provides common lifecycle methods and enforces the agent contract:
    single responsibility, budget enforcement, stop conditions, and
    structured observability per Coding Standards Section 4.

    Subclasses must implement:
        - execute: Core agent logic.
        - validate_input: Input validation before execution.
        - validate_output: Output validation after execution.
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent with configuration.

        Args:
            config: Agent configuration including model, prompt, and limits.
        """
        self._config = config
        self._logger = logging.getLogger(
            f"{__name__}.{config.agent_role}"
        )

    @property
    def config(self) -> AgentConfig:
        """Return the agent configuration."""
        return self._config

    @abstractmethod
    async def execute(self, message: AgentMessage, *, budget: Budget, budget_usage: BudgetUsage, correlation_id: str | None = None) -> AgentMessage:
        """Execute the agent's core logic.

        Args:
            message: Input message to process.
            budget: Budget constraints for this execution.
            budget_usage: Cumulative budget usage tracker.
            correlation_id: Optional tracing ID propagated through the
                VQMS orchestration pipeline.

        Returns:
            AgentMessage containing the agent's response.

        Raises:
            AgentError: When agent execution fails.
        """
        raise NotImplementedError("Pending implementation")

    @abstractmethod
    async def validate_input(self, message: AgentMessage, *, correlation_id: str | None = None) -> bool:
        """Validate input message before execution.

        Args:
            message: Input message to validate.
            correlation_id: Optional tracing ID propagated through the
                VQMS orchestration pipeline.

        Returns:
            True if input is valid, False otherwise.

        Raises:
            AgentError: When validation itself fails.
        """
        raise NotImplementedError("Pending implementation")

    @abstractmethod
    async def validate_output(self, message: AgentMessage, *, correlation_id: str | None = None) -> bool:
        """Validate output message after execution.

        Args:
            message: Output message to validate.
            correlation_id: Optional tracing ID propagated through the
                VQMS orchestration pipeline.

        Returns:
            True if output is valid, False otherwise.

        Raises:
            AgentError: When validation itself fails.
        """
        raise NotImplementedError("Pending implementation")
