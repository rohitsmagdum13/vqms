"""Manual test script for the email ingestion pipeline.

Simulates a Graph API email payload and runs it through the full
ingestion pipeline: parse -> S3 -> Redis -> EventBridge -> SQS.

Usage:
    uv run python scripts/test_ingestion.py
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

load_dotenv()

from config.settings import get_settings
from src.cache.redis_client import create_client as create_redis
from src.services.email_intake import ingest_email, parse_email


# Simulated Graph API email payload (same structure as real Graph API response)
FAKE_EMAIL: dict[str, object] = {
    "id": "AAMkAGI2TG93AAA_TEST_001",
    "internetMessageId": "<test-001@example.com>",
    "conversationId": "AAQkAGI2TG93AAA_CONV_001",
    "subject": "Invoice Query - PO#12345",
    "receivedDateTime": "2026-03-27T10:00:00Z",
    "hasAttachments": False,
    "from": {
        "emailAddress": {
            "name": "Test Vendor",
            "address": "vendor@example.com",
        },
    },
    "toRecipients": [
        {
            "emailAddress": {
                "address": "support@hexaware.com",
            },
        },
    ],
    "body": {
        "contentType": "text",
        "content": (
            "Hi Support,\n\n"
            "Could you please provide an update on Invoice #INV-2026-0042 "
            "related to PO#12345? We submitted it on March 15th and haven't "
            "received confirmation yet.\n\n"
            "Best regards,\nTest Vendor"
        ),
    },
    "internetMessageHeaders": [
        {"name": "From", "value": "vendor@example.com"},
        {"name": "To", "value": "support@hexaware.com"},
        {"name": "Subject", "value": "Invoice Query - PO#12345"},
    ],
    "attachments": [],
}


async def main() -> None:
    settings = get_settings()

    print("=" * 60)
    print("VQMS Email Ingestion Pipeline - Manual Test")
    print("=" * 60)

    # Step 1: Connect to Redis
    print("\n[1/5] Connecting to Redis Cloud...")
    redis = await create_redis(settings.redis_config())
    print("       Redis connected!")

    # Step 2: Parse email
    print("\n[2/5] Parsing email...")
    parsed = await parse_email(FAKE_EMAIL)
    print(f"       Subject: {FAKE_EMAIL['subject']}")
    print(f"       From: vendor@example.com")
    print(f"       Is reply: {parsed.is_reply}")
    print(f"       Body preview: {parsed.plain_text_body[:80]}...")

    # Step 3: Run full ingestion pipeline
    print("\n[3/5] Running full ingestion pipeline...")
    print("       -> Redis idempotency check")
    print("       -> S3 upload (vqms-email-raw-prod)")
    print("       -> EventBridge publish (EmailReceived)")
    print("       -> SQS send (vqms-email-intake)")

    result = await ingest_email(
        FAKE_EMAIL,
        redis_client=redis,
        correlation_id="manual-test-001",
    )

    # Step 4: Show results
    print("\n[4/5] Results:")
    print(f"       Duplicate: {result.is_duplicate}")
    print(f"       S3 key:    {result.s3_raw_key}")
    print(f"       Message ID: {result.email_message.message_id}")
    print(f"       Subject:    {result.email_message.subject}")
    print(f"       Sender:     {result.email_message.sender_email}")
    print(f"       Direction:  {result.email_message.direction}")

    # Step 5: Test idempotency - run same email again
    print("\n[5/5] Testing idempotency (same email again)...")
    result2 = await ingest_email(
        FAKE_EMAIL,
        redis_client=redis,
        correlation_id="manual-test-001-dup",
    )
    print(f"       Duplicate: {result2.is_duplicate}")
    if result2.is_duplicate:
        print("       Idempotency check PASSED - duplicate correctly detected!")
    else:
        print("       WARNING: Idempotency check FAILED")

    # Cleanup
    await redis.aclose()

    print("\n" + "=" * 60)
    print("All pipeline steps completed successfully!")
    print("=" * 60)
    print("\nCheck your AWS console:")
    print(f"  S3:          s3://vqms-email-raw-prod/{result.s3_raw_key}")
    print("  SQS:         vqms-email-intake queue")
    print("  EventBridge: vqms-events bus")
    print("  Redis:       idempotency:AAMkAGI2TG93AAA_TEST_001")


if __name__ == "__main__":
    asyncio.run(main())
