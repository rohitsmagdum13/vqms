-- Migration: 002_workflow_schema
-- Description: Creates the workflow schema with case_execution, ticket_link, and routing_decision tables.
-- Architecture Doc Section 4: workflow schema (3 tables)

CREATE SCHEMA IF NOT EXISTS workflow;

-- Case execution table: tracks the full lifecycle of processing a vendor email
CREATE TABLE IF NOT EXISTS workflow.case_execution (
    id                    BIGSERIAL PRIMARY KEY,
    case_id               TEXT NOT NULL UNIQUE,
    email_message_id      TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending', 'in_progress', 'awaiting_human', 'completed', 'failed', 'escalated')),
    current_step          TEXT NOT NULL DEFAULT 'intake',
    step_history          JSONB NOT NULL DEFAULT '[]'::jsonb,
    analysis_result       JSONB,                  -- Email analysis output (populated after Step 5A)
    vendor_id             TEXT,                    -- Resolved vendor ID (populated after Step 5B)
    ticket_number         TEXT,                    -- Created/updated ticket (populated after Step 8)
    routing_path          TEXT,                    -- Selected routing path (populated after Step 6)
    started_at            TIMESTAMPTZ NOT NULL,
    completed_at          TIMESTAMPTZ,
    error_message         TEXT,
    hop_count             INTEGER NOT NULL DEFAULT 0 CHECK (hop_count >= 0 AND hop_count <= 4),
    correlation_id        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_execution_email_message_id ON workflow.case_execution (email_message_id);
CREATE INDEX IF NOT EXISTS idx_case_execution_status ON workflow.case_execution (status);
CREATE INDEX IF NOT EXISTS idx_case_execution_correlation_id ON workflow.case_execution (correlation_id);

-- Ticket link table: maps email messages to ServiceNow tickets
CREATE TABLE IF NOT EXISTS workflow.ticket_link (
    id                    BIGSERIAL PRIMARY KEY,
    link_id               TEXT NOT NULL UNIQUE,
    email_message_id      TEXT NOT NULL,
    ticket_number         TEXT NOT NULL,
    link_type             TEXT NOT NULL CHECK (link_type IN ('created', 'updated', 'reopened')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ticket_link_email_message_id ON workflow.ticket_link (email_message_id);
CREATE INDEX IF NOT EXISTS idx_ticket_link_ticket_number ON workflow.ticket_link (ticket_number);

-- Routing decision table: records routing decisions made by the Orchestration Agent
CREATE TABLE IF NOT EXISTS workflow.routing_decision (
    id                    BIGSERIAL PRIMARY KEY,
    decision_id           TEXT NOT NULL UNIQUE,
    email_message_id      TEXT NOT NULL,
    routing_path          TEXT NOT NULL
                          CHECK (routing_path IN ('full_auto', 'low_confidence', 'existing_ticket', 'reopen', 'escalation')),
    confidence            DOUBLE PRECISION NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    reasoning             TEXT NOT NULL,
    vendor_id             TEXT,
    existing_ticket_number TEXT,
    escalation_level      INTEGER NOT NULL DEFAULT 0 CHECK (escalation_level >= 0 AND escalation_level <= 2),
    decided_at            TIMESTAMPTZ NOT NULL,
    correlation_id        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routing_decision_email_message_id ON workflow.routing_decision (email_message_id);
CREATE INDEX IF NOT EXISTS idx_routing_decision_routing_path ON workflow.routing_decision (routing_path);
