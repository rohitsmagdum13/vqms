# Data Privacy Policy

## PII Handling

- All PII is redacted before being sent to LLM providers (AWS Comprehend).
- PII is encrypted at rest using AES-256 and in transit using TLS 1.2+.
- Right-to-forget: Deletion cascades across vector stores, caches, and databases.

## Data Retention

- Session memory: 24h TTL
- Long-term memory: 180 days
- Audit logs: Per compliance requirements
