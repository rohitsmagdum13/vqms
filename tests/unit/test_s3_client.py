"""Unit tests for S3 client operations using moto mock."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from src.storage.s3_client import (
    S3ClientError,
    S3Config,
    VQMSBucket,
    delete_object,
    download_object,
    list_objects,
    upload_object,
)

_TEST_REGION = "us-east-1"
_TEST_BUCKET = VQMSBucket.EMAIL_RAW


def _cfg() -> S3Config:
    return S3Config(region=_TEST_REGION)


def _create_bucket() -> None:
    client = boto3.client("s3", region_name=_TEST_REGION)
    client.create_bucket(Bucket=str(_TEST_BUCKET))


class TestUploadObject:
    """Tests for upload_object."""

    @pytest.mark.asyncio
    async def test_upload_returns_key(self) -> None:
        with mock_aws():
            _create_bucket()
            key = await upload_object(
                _TEST_BUCKET,
                "2026/03/27/msg1.eml",
                b"raw email bytes",
                config=_cfg(),
                correlation_id="test-cid",
            )
            assert key == "2026/03/27/msg1.eml"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self) -> None:
        with mock_aws():
            _create_bucket()
            key = await upload_object(
                _TEST_BUCKET,
                "test/key.txt",
                b"data",
                content_type="text/plain",
                metadata={"source": "test"},
                config=_cfg(),
            )
            assert key == "test/key.txt"

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_bucket_raises(
        self,
    ) -> None:
        with mock_aws():
            with pytest.raises(
                S3ClientError, match="upload failed",
            ):
                await upload_object(
                    VQMSBucket.AUDIT_ARTIFACTS,
                    "key.txt",
                    b"data",
                    config=_cfg(),
                )


class TestDownloadObject:
    """Tests for download_object."""

    @pytest.mark.asyncio
    async def test_download_returns_bytes(self) -> None:
        with mock_aws():
            _create_bucket()
            content = b"test content"
            await upload_object(
                _TEST_BUCKET, "dl/test.txt", content,
                config=_cfg(),
            )
            result = await download_object(
                _TEST_BUCKET, "dl/test.txt",
                config=_cfg(),
            )
            assert result == content

    @pytest.mark.asyncio
    async def test_download_nonexistent_key_raises(
        self,
    ) -> None:
        with mock_aws():
            _create_bucket()
            with pytest.raises(
                S3ClientError, match="download failed",
            ):
                await download_object(
                    _TEST_BUCKET, "no/such/key.txt",
                    config=_cfg(),
                )


class TestDeleteObject:
    """Tests for delete_object."""

    @pytest.mark.asyncio
    async def test_delete_existing_object(self) -> None:
        with mock_aws():
            _create_bucket()
            await upload_object(
                _TEST_BUCKET, "del/test.txt", b"data",
                config=_cfg(),
            )
            await delete_object(
                _TEST_BUCKET, "del/test.txt",
                config=_cfg(),
            )
            keys = await list_objects(
                _TEST_BUCKET, "del/",
                config=_cfg(),
            )
            assert "del/test.txt" not in keys


class TestListObjects:
    """Tests for list_objects."""

    @pytest.mark.asyncio
    async def test_list_returns_matching_keys(self) -> None:
        with mock_aws():
            _create_bucket()
            await upload_object(
                _TEST_BUCKET, "list/a.txt", b"a",
                config=_cfg(),
            )
            await upload_object(
                _TEST_BUCKET, "list/b.txt", b"b",
                config=_cfg(),
            )
            await upload_object(
                _TEST_BUCKET, "other/c.txt", b"c",
                config=_cfg(),
            )
            keys = await list_objects(
                _TEST_BUCKET, "list/",
                config=_cfg(),
            )
            assert len(keys) == 2
            assert "list/a.txt" in keys
            assert "list/b.txt" in keys

    @pytest.mark.asyncio
    async def test_list_empty_prefix(self) -> None:
        with mock_aws():
            _create_bucket()
            keys = await list_objects(
                _TEST_BUCKET, "empty/",
                config=_cfg(),
            )
            assert keys == []
