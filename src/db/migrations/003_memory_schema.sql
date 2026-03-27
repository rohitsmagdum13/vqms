-- Migration: 003_memory_schema
-- Description: Creates the memory schema with vendor_profile_cache, episodic_memory, and embedding_index tables.
-- Architecture Doc Section 4: memory schema (3 tables)
-- Requires pgvector extension for embedding_index.

CREATE SCHEMA IF NOT EXISTS memory;

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Vendor profile cache table: persistent backing store for Redis vendor:{vendor_id} hot cache
CREATE TABLE IF NOT EXISTS memory.vendor_profile_cache (
    id                    BIGSERIAL PRIMARY KEY,
    vendor_id             TEXT NOT NULL UNIQUE,    -- Salesforce Account ID (cache key)
    vendor_name           TEXT NOT NULL,
    contact_email         TEXT NOT NULL,
    tier                  TEXT NOT NULL DEFAULT 'unclassified'
                          CHECK (tier IN ('platinum', 'gold', 'silver', 'bronze', 'unclassified')),
    sla_response_hours    INTEGER NOT NULL DEFAULT 24 CHECK (sla_response_hours >= 1),
    interaction_count     INTEGER NOT NULL DEFAULT 0 CHECK (interaction_count >= 0),
    last_interaction_at   TIMESTAMPTZ,
    cached_at             TIMESTAMPTZ NOT NULL,
    ttl_seconds           INTEGER NOT NULL DEFAULT 3600 CHECK (ttl_seconds >= 0),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vendor_profile_cache_contact_email ON memory.vendor_profile_cache (contact_email);

-- Episodic memory table: stores resolved cases for pattern matching and context enrichment
CREATE TABLE IF NOT EXISTS memory.episodic_memory (
    id                    BIGSERIAL PRIMARY KEY,
    memory_id             TEXT NOT NULL UNIQUE,
    vendor_id             TEXT NOT NULL,
    case_id               TEXT NOT NULL,
    email_message_id      TEXT NOT NULL,
    intent                TEXT NOT NULL,
    resolution_summary    TEXT NOT NULL,
    outcome               TEXT NOT NULL,
    tags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at            TIMESTAMPTZ NOT NULL,
    expires_at            TIMESTAMPTZ NOT NULL,    -- TTL (default 180 days per Section 3.2)
    correlation_id        TEXT NOT NULL,
    created_db_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodic_memory_vendor_id ON memory.episodic_memory (vendor_id);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_intent ON memory.episodic_memory (intent);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_expires_at ON memory.episodic_memory (expires_at);
CREATE INDEX IF NOT EXISTS idx_episodic_memory_tags ON memory.episodic_memory USING GIN (tags);

-- Embedding index table: pgvector-based semantic search for RAG retrieval
-- Default embedding dimension: 1024 (Amazon Titan Embed Text v2)
CREATE TABLE IF NOT EXISTS memory.embedding_index (
    id                    BIGSERIAL PRIMARY KEY,
    embedding_id          TEXT NOT NULL UNIQUE,
    source_type           TEXT NOT NULL CHECK (source_type IN ('email', 'ticket', 'knowledge_base')),
    source_id             TEXT NOT NULL,
    chunk_id              TEXT NOT NULL,
    content               TEXT NOT NULL,
    embedding             vector(1024) NOT NULL,   -- pgvector column (Titan v2 = 1024 dims)
    metadata              JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embedding_index_source ON memory.embedding_index (source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_embedding_index_metadata ON memory.embedding_index USING GIN (metadata);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_embedding_index_vector ON memory.embedding_index
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
