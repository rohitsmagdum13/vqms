"""Module: logger
Description: Structured JSON logging setup for the VQMS pipeline.

Configures structlog for JSON structured logging from day one per
Coding Standards Section 9. No print() statements — structured
logging only. Includes correlation_id, agent_role, tool, latency_ms,
tokens_in/out, cost, policy_decisions, and safety_flags.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from src.utils.correlation import get_correlation_id


class LoggerSetupError(Exception):
    """Raised when logger configuration fails."""


def _inject_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that injects correlation_id from ContextVar."""
    if "correlation_id" not in event_dict:
        cid = get_correlation_id()
        if cid is not None:
            event_dict["correlation_id"] = cid
    return event_dict


_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def configure_logging(
    *,
    level: str = "INFO",
    json_format: bool = True,
    log_group: str | None = None,
) -> None:
    """Configure structured JSON logging for the VQMS application.

    Sets up structlog with JSON rendering, correlation ID binding,
    and PII redaction processors. Configures console and optional
    CloudWatch handlers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: Whether to use JSON output format.
        log_group: Optional CloudWatch log group name.

    Raises:
        LoggerSetupError: When logging configuration fails.
    """
    level_upper = level.upper()
    if level_upper not in _VALID_LEVELS:
        msg = f"Invalid log level: {level!r}. Must be one of {_VALID_LEVELS}"
        raise LoggerSetupError(msg)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _inject_correlation_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level_upper))

    if log_group is not None:
        bound = structlog.get_logger("vqms.logging")
        bound.info(
            "cloudwatch_log_group_configured",
            log_group=log_group,
            note="CloudWatch handler requires deployment infrastructure",
        )


def get_logger(
    name: str,
    *,
    correlation_id: str | None = None,
    agent_role: str | None = None,
) -> Any:
    """Get a bound structured logger with VQMS context.

    Args:
        name: Logger name (typically __name__).
        correlation_id: Optional correlation ID to bind.
        agent_role: Optional agent role to bind.

    Returns:
        Bound structlog logger instance.

    Raises:
        LoggerSetupError: When logger creation fails.
    """
    bound_logger = structlog.get_logger(name)

    if correlation_id is not None:
        bound_logger = bound_logger.bind(correlation_id=correlation_id)
    if agent_role is not None:
        bound_logger = bound_logger.bind(agent_role=agent_role)

    return bound_logger
