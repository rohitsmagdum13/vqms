"""Module: s3_client
Description: S3 upload/download operations for the VQMS pipeline.

Manages object storage across the 4 VQMS S3 buckets defined in
the Architecture Doc Section 4: email-raw, email-attachments,
audit-artifacts, and knowledge-artifacts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3ClientError(Exception):
    """Raised when S3 operations fail."""


class VQMSBucket(StrEnum):
    """VQMS S3 bucket identifiers."""

    EMAIL_RAW = "vqms-email-raw-prod"
    EMAIL_ATTACHMENTS = "vqms-email-attachments-prod"
    AUDIT_ARTIFACTS = "vqms-audit-artifacts-prod"
    KNOWLEDGE_ARTIFACTS = "vqms-knowledge-artifacts-prod"


@dataclass(frozen=True)
class S3Config:
    """S3 client configuration.

    Attributes:
        region: AWS region for S3.
        endpoint_url: Optional custom endpoint (for local development).
    """

    region: str = "us-east-1"
    endpoint_url: str | None = None


def _build_client(config: S3Config | None) -> Any:
    """Build a boto3 S3 client from config."""
    cfg = config or S3Config()
    kwargs: dict[str, Any] = {"region_name": cfg.region}
    if cfg.endpoint_url is not None:
        kwargs["endpoint_url"] = cfg.endpoint_url
    return boto3.client("s3", **kwargs)


async def upload_object(
    bucket: VQMSBucket,
    key: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    metadata: dict[str, str] | None = None,
    config: S3Config | None = None,
    correlation_id: str | None = None,
) -> str:
    """Upload an object to an S3 bucket.

    Args:
        bucket: Target VQMS S3 bucket.
        key: S3 object key.
        data: Object content as bytes.
        content_type: MIME content type.
        metadata: Optional object metadata.
        config: S3 client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        S3 object key of the uploaded object.

    Raises:
        S3ClientError: When upload fails.
    """
    try:
        client = _build_client(config)
        put_kwargs: dict[str, Any] = {
            "Bucket": str(bucket),
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        if metadata:
            put_kwargs["Metadata"] = metadata
        client.put_object(**put_kwargs)
        logger.info(
            "s3_object_uploaded",
            extra={
                "bucket": str(bucket),
                "key": key,
                "size_bytes": len(data),
                "content_type": content_type,
                "correlation_id": correlation_id,
            },
        )
        return key
    except ClientError as exc:
        msg = f"S3 upload failed for {bucket}/{key}: {exc}"
        raise S3ClientError(msg) from exc


async def download_object(
    bucket: VQMSBucket,
    key: str,
    *,
    config: S3Config | None = None,
    correlation_id: str | None = None,
) -> bytes:
    """Download an object from an S3 bucket.

    Args:
        bucket: Source VQMS S3 bucket.
        key: S3 object key.
        config: S3 client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        Object content as bytes.

    Raises:
        S3ClientError: When download fails.
    """
    try:
        client = _build_client(config)
        response = client.get_object(Bucket=str(bucket), Key=key)
        data: bytes = response["Body"].read()
        logger.info(
            "s3_object_downloaded",
            extra={
                "bucket": str(bucket),
                "key": key,
                "size_bytes": len(data),
                "correlation_id": correlation_id,
            },
        )
        return data
    except ClientError as exc:
        msg = f"S3 download failed for {bucket}/{key}: {exc}"
        raise S3ClientError(msg) from exc


async def delete_object(
    bucket: VQMSBucket,
    key: str,
    *,
    config: S3Config | None = None,
    correlation_id: str | None = None,
) -> None:
    """Delete an object from an S3 bucket.

    Args:
        bucket: Target VQMS S3 bucket.
        key: S3 object key to delete.
        config: S3 client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Raises:
        S3ClientError: When deletion fails.
    """
    try:
        client = _build_client(config)
        client.delete_object(Bucket=str(bucket), Key=key)
        logger.info(
            "s3_object_deleted",
            extra={
                "bucket": str(bucket),
                "key": key,
                "correlation_id": correlation_id,
            },
        )
    except ClientError as exc:
        msg = f"S3 delete failed for {bucket}/{key}: {exc}"
        raise S3ClientError(msg) from exc


async def list_objects(
    bucket: VQMSBucket,
    prefix: str,
    *,
    max_keys: int = 1000,
    config: S3Config | None = None,
    correlation_id: str | None = None,
) -> list[str]:
    """List object keys in an S3 bucket with a given prefix.

    Args:
        bucket: Target VQMS S3 bucket.
        prefix: Key prefix to filter by.
        max_keys: Maximum number of keys to return.
        config: S3 client configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of S3 object keys matching the prefix.

    Raises:
        S3ClientError: When listing fails.
    """
    try:
        client = _build_client(config)
        response = client.list_objects_v2(
            Bucket=str(bucket),
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        keys: list[str] = [
            obj["Key"]
            for obj in response.get("Contents", [])
        ]
        logger.debug(
            "s3_objects_listed",
            extra={
                "bucket": str(bucket),
                "prefix": prefix,
                "count": len(keys),
                "correlation_id": correlation_id,
            },
        )
        return keys
    except ClientError as exc:
        msg = (
            f"S3 list failed for {bucket}"
            f" prefix={prefix!r}: {exc}"
        )
        raise S3ClientError(msg) from exc
