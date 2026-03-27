"""Module: factory
Description: Model instance factory for the VQMS pipeline.

Creates and configures LLM client instances based on model configuration.
Supports primary and fallback model chains per Coding Standards Section 6.
All model access goes through the Bedrock Integration Service.
"""

from __future__ import annotations

import logging
from typing import Any

from src.adapters.bedrock import BedrockConfig, LLMClient

logger = logging.getLogger(__name__)


class ModelFactoryError(Exception):
    """Raised when model factory operations fail."""


async def create_client(config: BedrockConfig, *, correlation_id: str | None = None) -> LLMClient:
    """Create an LLM client instance configured for the Bedrock Integration Service.

    Args:
        config: Bedrock service configuration with model IDs and region.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        LLMClient instance implementing the Protocol interface.

    Raises:
        ModelFactoryError: When client creation fails.
    """
    raise NotImplementedError("Pending implementation")


async def get_model_chain(*, config: BedrockConfig, correlation_id: str | None = None) -> list[str]:
    """Get the model fallback chain (primary -> fallback).

    Returns the ordered list of model IDs to try for completion
    requests, implementing the fallback strategy from Section 6.

    Args:
        config: Bedrock service configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        Ordered list of model IDs for the fallback chain.

    Raises:
        ModelFactoryError: When chain construction fails.
    """
    raise NotImplementedError("Pending implementation")


async def get_embedding_model(*, config: BedrockConfig, correlation_id: str | None = None) -> Any:
    """Get the embedding model client.

    Args:
        config: Bedrock service configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        Embedding model client instance.

    Raises:
        ModelFactoryError: When model retrieval fails.
    """
    raise NotImplementedError("Pending implementation")
