-- Migration: 005_reporting_schema
-- Description: Creates the reporting schema with sla_metrics table.
-- Architecture Doc Section 4: reporting schema (1 table)

CREATE SCHEMA IF NOT EXISTS reporting;

-- SLA metrics table: aggregated SLA performance data for dashboards
CREATE TABLE IF NOT EXISTS reporting.sla_metrics (
    id                    BIGSERIAL PRIMARY KEY,
    ticket_number         TEXT NOT NULL,
    vendor_id             TEXT NOT NULL,
    vendor_tier           TEXT NOT NULL,
    sla_deadline          TIMESTAMPTZ NOT NULL,
    response_at           TIMESTAMPTZ,             -- When the first response was sent
    resolution_at         TIMESTAMPTZ,             -- When the ticket was resolved
    sla_response_hours    INTEGER NOT NULL,         -- Configured SLA response time
    actual_response_hours DOUBLE PRECISION,         -- Actual response time in hours
    sla_breached          BOOLEAN NOT NULL DEFAULT FALSE,
    escalation_level      INTEGER NOT NULL DEFAULT 0 CHECK (escalation_level >= 0 AND escalation_level <= 2),
    routing_path          TEXT,
    correlation_id        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sla_metrics_vendor_id ON reporting.sla_metrics (vendor_id);
CREATE INDEX IF NOT EXISTS idx_sla_metrics_vendor_tier ON reporting.sla_metrics (vendor_tier);
CREATE INDEX IF NOT EXISTS idx_sla_metrics_sla_breached ON reporting.sla_metrics (sla_breached);
CREATE INDEX IF NOT EXISTS idx_sla_metrics_created_at ON reporting.sla_metrics (created_at DESC);
