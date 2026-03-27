"""Module: helpers
Description: General helper functions for the VQMS pipeline.

Provides utility functions used across multiple modules:
timestamp formatting, JSON serialization helpers, and
common data transformation operations.
"""

from __future__ import annotations

import dataclasses
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import orjson
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HelperError(Exception):
    """Raised when helper operations fail."""


def _json_default(obj: object) -> object:
    """Custom serializer for types orjson doesn't handle natively."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def utc_now() -> datetime:
    """Get the current UTC timestamp.

    Returns:
        Timezone-aware UTC datetime.

    Raises:
        HelperError: When timestamp generation fails.
    """
    return datetime.now(UTC)


def safe_json_serialize(obj: Any) -> str:
    """Serialize an object to JSON with safe handling of non-serializable types.

    Handles datetime, Enum, pydantic models, and dataclasses.

    Args:
        obj: Object to serialize.

    Returns:
        JSON string representation.

    Raises:
        HelperError: When serialization fails.
    """
    try:
        return orjson.dumps(obj, default=_json_default).decode("utf-8")
    except TypeError as exc:
        raise HelperError(f"JSON serialization failed: {exc}") from exc


def truncate_for_log(text: str, max_length: int = 500) -> str:
    """Truncate text for safe inclusion in log entries.

    Args:
        text: Text to truncate.
        max_length: Maximum length in characters.

    Returns:
        Truncated text with ellipsis if exceeded.

    Raises:
        HelperError: When truncation fails.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...[truncated]"
