-- Migration: 004_audit_schema
-- Description: Creates the audit schema with action_log and validation_results tables.
-- Architecture Doc Section 4: audit schema (2 tables)
-- Every side-effect writes to audit.action_log from day one.

CREATE SCHEMA IF NOT EXISTS audit;

-- Action log table: records every side-effect in the pipeline for audit trail
CREATE TABLE IF NOT EXISTS audit.action_log (
    id                    BIGSERIAL PRIMARY KEY,
    action_id             TEXT NOT NULL UNIQUE,
    correlation_id        TEXT NOT NULL,
    agent_role            TEXT,                    -- Which agent performed the action
    tool                  TEXT,                    -- Which tool was invoked
    action                TEXT NOT NULL,           -- Action type (e.g., email_fetched, ticket_created)
    target_type           TEXT,                    -- Target entity type (email, ticket, vendor)
    target_id             TEXT,                    -- Target entity identifier
    input_summary         JSONB,                   -- Sanitized input summary (no PII)
    output_summary        JSONB,                   -- Sanitized output summary (no PII)
    result_status         TEXT NOT NULL CHECK (result_status IN ('success', 'failure', 'partial')),
    error_message         TEXT,
    latency_ms            DOUBLE PRECISION,
    tokens_in             INTEGER,
    tokens_out            INTEGER,
    cost_usd              DOUBLE PRECISION,
    policy_decisions      JSONB,                   -- Policy evaluation results
    safety_flags          JSONB,                   -- Content moderation flags
    user_id_hash          TEXT,                    -- Hashed user ID (never raw PII)
    performed_at          TIMESTAMPTZ NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_log_correlation_id ON audit.action_log (correlation_id);
CREATE INDEX IF NOT EXISTS idx_action_log_action ON audit.action_log (action);
CREATE INDEX IF NOT EXISTS idx_action_log_agent_role ON audit.action_log (agent_role);
CREATE INDEX IF NOT EXISTS idx_action_log_performed_at ON audit.action_log (performed_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_log_result_status ON audit.action_log (result_status);

-- Validation results table: records Quality & Governance Gate outcomes
-- Artifacts stored in vqms-audit-artifacts-prod S3 bucket
CREATE TABLE IF NOT EXISTS audit.validation_results (
    id                    BIGSERIAL PRIMARY KEY,
    report_id             TEXT NOT NULL UNIQUE,
    draft_id              TEXT NOT NULL,
    status                TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'requires_review')),
    checks                JSONB NOT NULL DEFAULT '[]'::jsonb,
    ticket_number_valid   BOOLEAN NOT NULL DEFAULT FALSE,
    sla_wording_valid     BOOLEAN NOT NULL DEFAULT FALSE,
    template_compliant    BOOLEAN NOT NULL DEFAULT FALSE,
    pii_detected          BOOLEAN NOT NULL DEFAULT FALSE,
    pii_details           JSONB NOT NULL DEFAULT '[]'::jsonb,
    governance_policy_met BOOLEAN NOT NULL DEFAULT FALSE,
    s3_artifact_key       TEXT,                    -- S3 key for detailed report artifact
    validated_at          TIMESTAMPTZ NOT NULL,
    correlation_id        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_results_draft_id ON audit.validation_results (draft_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_status ON audit.validation_results (status);
CREATE INDEX IF NOT EXISTS idx_validation_results_correlation_id ON audit.validation_results (correlation_id);
