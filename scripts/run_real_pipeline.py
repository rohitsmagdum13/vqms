"""Real email ingestion pipeline - fetches from Outlook mailbox.

Supports two modes:
  - Work/School account: automatic (client_credentials, no browser needed)
  - Personal account:    device code flow (sign in via browser once)

Detects account type automatically from GRAPH_API_MAILBOX.

Usage:
    uv run python scripts/run_real_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()

import httpx
import msal

from config.settings import get_settings
from src.cache.redis_client import create_client as create_redis
from src.services.email_intake import ingest_email


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------

def acquire_token_work_account(settings: object) -> str:
    """Acquire token via client_credentials (work/school accounts)."""
    try:
        app = msal.ConfidentialClientApplication(
            settings.graph_api_client_id,
            authority=f"https://login.microsoftonline.com/{settings.graph_api_tenant_id}",
            client_credential=settings.graph_api_client_secret,
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"],
        )
        if "access_token" in result:
            print("    Token acquired (client_credentials)!")
            return result["access_token"]
        else:
            raise RuntimeError(
                f"{result.get('error')}: {result.get('error_description')}"
            )
    except Exception as exc:
        print(f"    ERROR acquiring work token: {exc}")
        raise


def acquire_token_personal_account(settings: object) -> str:
    """Acquire token via device code flow (personal Outlook.com accounts)."""
    try:
        app = msal.PublicClientApplication(
            settings.graph_api_client_id,
            authority="https://login.microsoftonline.com/consumers",
        )
        flow = app.initiate_device_flow(scopes=["Mail.Read", "Mail.ReadWrite"])
        if "user_code" not in flow:
            raise RuntimeError(
                f"Device flow failed: {json.dumps(flow, indent=2)}"
            )

        print("")
        print("    " + "=" * 52)
        print("      SIGN IN REQUIRED (personal account)")
        print("    " + "=" * 52)
        print(f"      1. Open:  {flow['verification_uri']}")
        print(f"      2. Enter: {flow['user_code']}")
        print(f"      3. Sign in with: {settings.graph_api_mailbox}")
        print("    " + "=" * 52)
        print("      Waiting for sign-in...")
        print("")

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            print("    Token acquired (device code)!")
            return result["access_token"]
        else:
            raise RuntimeError(
                f"{result.get('error')}: {result.get('error_description')}"
            )
    except Exception as exc:
        print(f"    ERROR acquiring personal token: {exc}")
        raise


def acquire_token(settings: object) -> str:
    """Auto-detect account type and acquire token."""
    mailbox = settings.graph_api_mailbox.lower()
    is_personal = mailbox.endswith((
        "@outlook.com", "@hotmail.com", "@live.com", "@msn.com",
    ))

    if is_personal:
        print(f"    Detected personal account: {mailbox}")
        return acquire_token_personal_account(settings)
    else:
        print(f"    Detected work account: {mailbox}")
        return acquire_token_work_account(settings)


# ---------------------------------------------------------------------------
# Email fetching
# ---------------------------------------------------------------------------

async def fetch_real_emails(
    token: str,
    mailbox: str,
    *,
    is_personal: bool,
    max_results: int = 10,
) -> list:
    """Fetch unread emails from the mailbox.

    Work accounts use /users/{mailbox} (application permissions).
    Personal accounts use /me (delegated permissions).
    """
    if is_personal:
        base_url = "https://graph.microsoft.com/v1.0/me"
    else:
        base_url = f"https://graph.microsoft.com/v1.0/users/{mailbox}"

    url = f"{base_url}/mailFolders/inbox/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "$top": str(max_results),
        "$orderby": "receivedDateTime desc",
        "$filter": "isRead eq false",
        "$select": (
            "id,internetMessageId,conversationId,subject,"
            "receivedDateTime,hasAttachments,isRead,from,"
            "toRecipients,body,internetMessageHeaders"
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 200:
            return resp.json().get("value", [])
        else:
            error_body = resp.text[:500] if resp.text else "(empty response)"
            print(f"    ERROR: HTTP {resp.status_code}")
            print(f"    {error_body}")
            return []
    except httpx.TimeoutException:
        print("    ERROR: Request timed out connecting to Graph API")
        return []
    except Exception as exc:
        print(f"    ERROR fetching emails: {exc}")
        return []


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def main() -> None:
    settings = get_settings()
    mailbox = settings.graph_api_mailbox
    is_personal = mailbox.lower().endswith((
        "@outlook.com", "@hotmail.com", "@live.com", "@msn.com",
    ))

    print("")
    print("=" * 60)
    print("  VQMS Real Email Ingestion Pipeline")
    print(f"  Mailbox: {mailbox}")
    print(f"  Type:    {'Personal' if is_personal else 'Work/School'}")
    print("=" * 60)
    print("")

    # --- Step 1: Acquire token ---
    print("[1] Acquiring Graph API token...")
    try:
        token = acquire_token(settings)
    except Exception:
        print("")
        print("FATAL: Cannot acquire token. Check your .env credentials:")
        print("  GRAPH_API_TENANT_ID")
        print("  GRAPH_API_CLIENT_ID")
        print("  GRAPH_API_CLIENT_SECRET")
        return
    print("")

    # --- Step 2: Connect to Redis ---
    print("[2] Connecting to Redis Cloud...")
    redis_client = None
    try:
        redis_client = await create_redis(settings.redis_config())
        print("    Connected!")
    except Exception as exc:
        print(f"    WARNING: Redis connection failed: {exc}")
        print("    Continuing without idempotency checks...")
    print("")

    # --- Step 3: Fetch real emails ---
    print(f"[3] Fetching unread emails from {mailbox}...")
    try:
        emails = await fetch_real_emails(
            token, mailbox, is_personal=is_personal,
        )
    except Exception as exc:
        print(f"    ERROR: {exc}")
        emails = []

    print(f"    Found {len(emails)} unread emails")
    print("")

    if not emails:
        print("    No unread emails found.")
        print(f"    Send a test email to {mailbox} and run again.")
        if redis_client:
            await redis_client.aclose()
        return

    # --- Step 4: Ingest each email ---
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, email in enumerate(emails, 1):
        sender = email.get("from", {}).get("emailAddress", {}).get("address", "?")
        subject = email.get("subject", "(no subject)")

        print(f"[4.{i}] {subject}")
        print(f"       From: {sender}")

        try:
            result = await ingest_email(
                email,
                redis_client=redis_client,
            )

            if result.is_duplicate:
                print("       -> SKIPPED (duplicate)")
                skip_count += 1
            else:
                print(f"       -> S3:     {result.s3_raw_key}")
                print(f"       -> SQS:    vqms-email-intake")
                print(f"       -> Event:  EmailReceived")
                print(f"       -> Reply:  {result.parsed_payload.is_reply}")
                success_count += 1
            print("       -> Status: OK")

        except Exception as exc:
            fail_count += 1
            print(f"       -> FAILED: {exc}")
            traceback.print_exc()

        print("")

    # --- Step 5: Cleanup ---
    if redis_client:
        try:
            await redis_client.aclose()
        except Exception:
            pass

    # --- Summary ---
    print("=" * 60)
    print("  Pipeline Complete!")
    print("=" * 60)
    print(f"  Total emails:  {len(emails)}")
    print(f"  Ingested:      {success_count}")
    print(f"  Duplicates:    {skip_count}")
    print(f"  Failed:        {fail_count}")
    print("")
    if success_count > 0:
        print("  Check your AWS console:")
        print("    S3:          vqms-email-raw-prod bucket")
        print("    SQS:         vqms-email-intake queue")
        print("    EventBridge: vqms-events bus")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
