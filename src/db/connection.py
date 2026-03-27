"""Module: connection
Description: PostgreSQL connection pool management for the VQMS pipeline.

Provides async connection pooling via asyncpg with pgvector extension
support. Manages connection lifecycle, health checks, and schema
initialization for the 5 VQMS database schemas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection operations fail."""


@dataclass(frozen=True)
class DatabaseConfig:
    """PostgreSQL connection configuration.

    Attributes:
        host: Database host.
        port: Database port.
        database: Database name.
        user: Database user.
        min_connections: Minimum pool connections.
        max_connections: Maximum pool connections.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = "vqms"
    user: str = "vqms"
    min_connections: int = 5
    max_connections: int = 20


async def create_pool(
    config: DatabaseConfig,
    *,
    correlation_id: str | None = None,
) -> asyncpg.Pool:
    """Create an asyncpg connection pool.

    Initializes the pool with pgvector extension support and
    configures connection settings for the VQMS schemas.

    Args:
        config: Database connection configuration.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        asyncpg connection pool instance.

    Raises:
        DatabaseConnectionError: When pool creation fails.
    """
    try:
        pool: asyncpg.Pool = await asyncpg.create_pool(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            min_size=config.min_connections,
            max_size=config.max_connections,
        )
        logger.info(
            "database_pool_created",
            extra={
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "min_size": config.min_connections,
                "max_size": config.max_connections,
                "correlation_id": correlation_id,
            },
        )
        return pool
    except Exception as exc:
        msg = f"Failed to create database pool: {exc}"
        raise DatabaseConnectionError(msg) from exc


async def close_pool(pool: Any, *, correlation_id: str | None = None) -> None:
    """Gracefully close the connection pool.

    Args:
        pool: asyncpg connection pool to close.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Raises:
        DatabaseConnectionError: When pool closure fails.
    """
    try:
        await pool.close()
        logger.info("database_pool_closed", extra={"correlation_id": correlation_id})
    except Exception as exc:
        msg = f"Failed to close database pool: {exc}"
        raise DatabaseConnectionError(msg) from exc


async def health_check(pool: Any, *, correlation_id: str | None = None) -> bool:
    """Check database connectivity and pool health.

    Args:
        pool: asyncpg connection pool to check.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        True if the database is reachable and the pool is healthy.

    Raises:
        DatabaseConnectionError: When health check fails.
    """
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
        logger.debug(
            "database_health_check",
            extra={"result": result, "correlation_id": correlation_id},
        )
        return bool(result == 1)
    except Exception as exc:
        msg = f"Database health check failed: {exc}"
        raise DatabaseConnectionError(msg) from exc


async def run_migrations(
    pool: Any,
    *,
    migrations_dir: str = "src/db/migrations",
    correlation_id: str | None = None,
) -> list[str]:
    """Execute pending SQL migration scripts in order.

    Reads migration files from the migrations directory and executes
    them in sequence. Tracks applied migrations to avoid re-execution.

    Args:
        pool: asyncpg connection pool.
        migrations_dir: Path to the migrations directory.
        correlation_id: Optional tracing ID propagated through the
            VQMS orchestration pipeline.

    Returns:
        List of applied migration filenames.

    Raises:
        DatabaseConnectionError: When migration execution fails.
    """
    migrations_path = Path(migrations_dir)
    if not migrations_path.is_dir():
        msg = f"Migrations directory not found: {migrations_dir}"
        raise DatabaseConnectionError(msg)

    sql_files = sorted(migrations_path.glob("*.sql"))
    if not sql_files:
        logger.info("no_migrations_found", extra={"correlation_id": correlation_id})
        return []

    applied: list[str] = []
    try:
        async with pool.acquire() as conn:
            # Create tracking table if not exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS public.schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            already_applied: set[str] = {
                row["filename"]
                for row in await conn.fetch(
                    "SELECT filename FROM public.schema_migrations"
                )
            }

            for sql_file in sql_files:
                if sql_file.name in already_applied:
                    logger.debug(
                        "migration_skipped",
                        extra={
                            "filename": sql_file.name,
                            "correlation_id": correlation_id,
                        },
                    )
                    continue

                sql = sql_file.read_text(encoding="utf-8")
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO public.schema_migrations (filename) VALUES ($1)",
                        sql_file.name,
                    )
                applied.append(sql_file.name)
                logger.info(
                    "migration_applied",
                    extra={"filename": sql_file.name, "correlation_id": correlation_id},
                )

    except DatabaseConnectionError:
        raise
    except Exception as exc:
        msg = f"Migration execution failed: {exc}"
        raise DatabaseConnectionError(msg) from exc

    return applied
