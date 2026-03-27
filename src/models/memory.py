"""Module: memory
Description: Pydantic models for the four-tier memory system in the VQMS pipeline.

Defines EpisodicMemory, VendorProfileCache, and EmbeddingRecord models.
Maps to memory.episodic_memory, memory.vendor_profile_cache, and
memory.embedding_index PostgreSQL tables (Architecture Doc Section 4).
"""

from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class EpisodicMemory(BaseModel):
    """Episodic memory record for storing past interaction context.

    Part of the long-term memory tier. Stores resolved cases and their
    outcomes for pattern matching and context enrichment in future queries.
    Maps to memory.episodic_memory table.

    Attributes:
        memory_id: Unique memory record identifier.
        vendor_id: Associated vendor Salesforce ID.
        case_id: Associated workflow case execution ID.
        email_message_id: Originating email message ID.
        intent: Classified intent of the original email.
        resolution_summary: Summary of how the case was resolved.
        outcome: Final outcome (resolved, escalated, etc.).
        tags: Searchable tags for retrieval.
        created_at: Memory creation timestamp.
        expires_at: TTL expiration timestamp (180 days default).
        correlation_id: Tracing ID from the original pipeline execution.
    """

    memory_id: str = Field(..., description="Unique memory record ID")
    vendor_id: str = Field(..., description="Associated vendor Salesforce ID")
    case_id: str = Field(..., description="Associated case execution ID")
    email_message_id: str = Field(..., description="Originating email message ID")
    intent: str = Field(..., description="Classified email intent")
    resolution_summary: str = Field(..., description="Resolution summary")
    outcome: str = Field(..., description="Final outcome")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    created_at: datetime = Field(..., description="Memory creation timestamp")
    expires_at: datetime = Field(..., description="TTL expiration timestamp")
    correlation_id: str = Field(..., description="Original pipeline correlation ID")


class VendorProfileCache(BaseModel):
    """Cached vendor profile for fast lookup during pipeline execution.

    Part of the hot cache tier (Redis vendor:{vendor_id} key family)
    with PostgreSQL backing store in memory.vendor_profile_cache table.

    Attributes:
        vendor_id: Salesforce Account ID (cache key).
        vendor_name: Company name.
        contact_email: Primary contact email.
        tier: Vendor tier classification.
        sla_response_hours: SLA response time in hours.
        interaction_count: Total historical interactions.
        last_interaction_at: Timestamp of most recent interaction.
        cached_at: When this record was cached.
        ttl_seconds: Time-to-live for this cache entry.
    """

    vendor_id: str = Field(..., description="Salesforce Account ID (cache key)")
    vendor_name: str = Field(..., description="Company name")
    contact_email: str = Field(..., description="Primary contact email")
    tier: str = Field(default="unclassified", description="Vendor tier")
    sla_response_hours: int = Field(default=24, description="SLA response hours")
    interaction_count: int = Field(
        default=0, ge=0, description="Total historical interactions"
    )
    last_interaction_at: datetime | None = Field(
        default=None, description="Most recent interaction timestamp"
    )
    cached_at: datetime = Field(..., description="Cache timestamp")
    ttl_seconds: int = Field(default=3600, ge=0, description="Cache TTL in seconds")

    @field_validator("contact_email")
    @classmethod
    def _validate_contact_email(cls, v: str) -> str:
        if "@" not in v:
            msg = f"Invalid contact email format: {v!r}"
            raise ValueError(msg)
        return v.strip().lower()


class EmbeddingRecord(BaseModel):
    """Vector embedding record for semantic search in the VQMS knowledge base.

    Maps to memory.embedding_index table with pgvector extension.
    Used by the Memory & Context Service for RAG retrieval.

    Attributes:
        embedding_id: Unique embedding record identifier.
        source_type: Type of source document (email, ticket, knowledge_base).
        source_id: ID of the source document.
        chunk_id: Chunk identifier within the source document.
        content: Text content that was embedded.
        embedding: Vector embedding (stored as pgvector).
        metadata: Additional metadata for filtering (tenant, language, etc.).
        created_at: Embedding creation timestamp.
    """

    embedding_id: str = Field(..., description="Unique embedding record ID")
    source_type: str = Field(
        ..., description="Source type: email, ticket, knowledge_base"
    )
    source_id: str = Field(..., description="Source document ID")
    chunk_id: str = Field(..., description="Chunk ID within source")
    content: str = Field(..., description="Text content that was embedded")
    embedding: list[float] = Field(..., description="Vector embedding")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Filtering metadata"
    )
    created_at: datetime = Field(..., description="Embedding creation timestamp")

    @field_validator("embedding")
    @classmethod
    def _validate_embedding_dimensions(cls, v: list[float]) -> list[float]:
        if len(v) == 0:
            msg = "Embedding vector must not be empty"
            raise ValueError(msg)
        return v
