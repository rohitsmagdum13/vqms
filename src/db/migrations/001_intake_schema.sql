-- Migration: 001_intake_schema
-- Description: Creates the intake schema with email_messages and email_attachments tables.
-- Architecture Doc Section 4: intake schema (2 tables)

CREATE SCHEMA IF NOT EXISTS intake;

-- Email messages table: stores metadata for ingested emails
-- Idempotency key: message_id (Microsoft Graph API message ID)
CREATE TABLE IF NOT EXISTS intake.email_messages (
    id                    BIGSERIAL PRIMARY KEY,
    message_id            TEXT NOT NULL UNIQUE,  -- Graph API message ID (idempotency key)
    internet_message_id   TEXT NOT NULL,          -- RFC 2822 Message-ID header
    conversation_id       TEXT NOT NULL,          -- Graph API conversation/thread ID
    subject               TEXT NOT NULL,
    sender_email          TEXT NOT NULL,
    sender_name           TEXT NOT NULL DEFAULT '',
    recipients            JSONB NOT NULL DEFAULT '[]'::jsonb,
    received_at           TIMESTAMPTZ NOT NULL,
    direction             TEXT NOT NULL DEFAULT 'inbound' CHECK (direction IN ('inbound', 'outbound')),
    s3_raw_key            TEXT NOT NULL,          -- S3 key in vqms-email-raw-prod
    has_attachments       BOOLEAN NOT NULL DEFAULT FALSE,
    correlation_id        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_email_messages_conversation_id ON intake.email_messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_sender_email ON intake.email_messages (sender_email);
CREATE INDEX IF NOT EXISTS idx_email_messages_received_at ON intake.email_messages (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_correlation_id ON intake.email_messages (correlation_id);

-- Email attachments table: stores metadata for email attachments
-- Actual files stored in vqms-email-attachments-prod S3 bucket
CREATE TABLE IF NOT EXISTS intake.email_attachments (
    id                    BIGSERIAL PRIMARY KEY,
    attachment_id         TEXT NOT NULL UNIQUE,
    email_message_id      TEXT NOT NULL REFERENCES intake.email_messages (message_id) ON DELETE CASCADE,
    filename              TEXT NOT NULL,
    content_type          TEXT NOT NULL,
    size_bytes            BIGINT NOT NULL CHECK (size_bytes >= 0),
    s3_key                TEXT NOT NULL,          -- S3 key in vqms-email-attachments-prod
    checksum_sha256       TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_attachments_email_message_id ON intake.email_attachments (email_message_id);
