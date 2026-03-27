"""Redis cache layer for VQMS.

Contains the Redis connection wrapper with key-pattern helpers
for the 6 Redis key families: idempotency, thread, ticket,
workflow, vendor, sla.
"""
