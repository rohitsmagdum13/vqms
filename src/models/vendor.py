"""Module: vendor
Description: Pydantic models for vendor resolution in the VQMS pipeline.

Defines VendorProfile, VendorMatch, and VendorTier models used by the
Vendor Resolution Service (Step 5B) when querying Salesforce CRM.
Maps to memory.vendor_profile_cache PostgreSQL table.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VendorTier(StrEnum):
    """Vendor tier classification determining SLA and routing priority."""

    PLATINUM = "platinum"
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    UNCLASSIFIED = "unclassified"


class VendorProfile(BaseModel):
    """Vendor profile retrieved from Salesforce CRM.

    Cached in memory.vendor_profile_cache table and Redis vendor:{vendor_id}
    key family for fast lookup during pipeline execution.

    Attributes:
        vendor_id: Salesforce Account ID.
        vendor_name: Company name from Salesforce.
        contact_email: Primary contact email address.
        tier: Vendor tier classification.
        sla_response_hours: SLA response time in hours based on tier.
        account_manager: Assigned account manager name.
        active: Whether the vendor account is active.
        last_synced_at: Timestamp of last Salesforce sync.
        metadata: Additional Salesforce fields as key-value pairs.
    """

    vendor_id: str = Field(..., description="Salesforce Account ID")
    vendor_name: str = Field(..., description="Company name from Salesforce")
    contact_email: str = Field(..., description="Primary contact email")
    tier: VendorTier = Field(
        default=VendorTier.UNCLASSIFIED, description="Vendor tier"
    )
    sla_response_hours: int = Field(
        default=24, ge=1, description="SLA response time in hours"
    )
    account_manager: str = Field(default="", description="Account manager name")
    active: bool = Field(default=True, description="Active account flag")
    last_synced_at: datetime | None = Field(
        default=None, description="Last Salesforce sync timestamp"
    )
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional Salesforce fields"
    )


class VendorMatch(BaseModel):
    """Result of the vendor resolution lookup process.

    Produced by the Vendor Resolution Service using the three-step
    fallback chain: email match -> vendor ID fallback -> name similarity.

    Attributes:
        vendor_profile: Matched vendor profile (None if unresolved).
        match_method: Method used to resolve the vendor.
        confidence: Confidence score of the match (0.0 to 1.0).
        resolved: Whether the vendor was successfully resolved.
        correlation_id: Tracing ID propagated through the pipeline.
    """

    vendor_profile: VendorProfile | None = Field(
        default=None, description="Matched vendor profile"
    )
    match_method: str = Field(
        default="none",
        description="Resolution method: email_exact, vendor_id, name_similarity, none",
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Match confidence"
    )
    resolved: bool = Field(default=False, description="Successfully resolved flag")
    correlation_id: str = Field(..., description="Pipeline correlation ID")
