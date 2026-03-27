"""Module: settings
Description: Centralized settings loaded from .env using pydantic BaseSettings.

Reads all environment variables defined in .env.copy and exposes
factory methods to build the frozen Config dataclasses used across
the VQMS pipeline. This is the single place where .env values are
read — no other module should call os.getenv() for configuration.

Usage:
    from config.settings import get_settings

    settings = get_settings()              # cached singleton
    s3_cfg   = settings.s3_config()        # -> S3Config
    sqs_cfg  = settings.sqs_config()       # -> SQSConfig
    eb_cfg   = settings.eventbridge_config()
    gql_cfg  = settings.graph_api_config()
    db_cfg   = settings.database_config()
    redis_cfg = settings.redis_config()
    bedrock_cfg = settings.bedrock_config()
"""

from __future__ import annotations

import functools

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.adapters.bedrock import BedrockConfig
from src.adapters.graph_api import GraphAPIConfig
from src.adapters.salesforce import SalesforceConfig
from src.adapters.servicenow import ServiceNowConfig
from src.cache.redis_client import RedisConfig
from src.db.connection import DatabaseConfig
from src.events.eventbridge import EventBridgeConfig
from src.queues.sqs import SQSConfig
from src.storage.s3_client import S3Config


class Settings(BaseSettings):
    """VQMS application settings — loaded from .env automatically.

    Every field maps to an environment variable by name (case-insensitive).
    Defaults match the values in .env.copy so the app runs locally
    without any .env file for AWS services that read credentials
    from ~/.aws/credentials or IAM roles.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_env: str = "development"
    app_name: str = "vqms"
    app_debug: bool = True
    app_port: int = 8000
    log_level: str = "DEBUG"

    # --- AWS General ---
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""

    # --- Amazon Bedrock ---
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_region: str = "us-east-1"
    bedrock_max_tokens: int = 4096
    bedrock_temperature: float = 0.1
    bedrock_fallback_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_max_retries: int = 3
    bedrock_timeout_seconds: int = 30

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vqms"
    postgres_user: str = "vqms"
    postgres_password: str = ""
    postgres_pool_min: int = 5
    postgres_pool_max: int = 20

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_ssl: bool = False

    # --- Microsoft Graph API ---
    graph_api_tenant_id: str = ""
    graph_api_client_id: str = ""
    graph_api_client_secret: str = ""
    graph_api_access_token: str = ""
    graph_api_mailbox: str = ""
    graph_api_poll_interval_seconds: int = 60

    # --- Salesforce ---
    salesforce_instance_url: str = ""
    salesforce_username: str = ""
    salesforce_password: str = ""
    salesforce_security_token: str = ""

    # --- ServiceNow ---
    servicenow_instance_url: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""

    # --- S3 ---
    s3_bucket_email_raw: str = "vqms-email-raw-prod"
    s3_bucket_attachments: str = "vqms-email-attachments-prod"
    s3_bucket_audit_artifacts: str = "vqms-audit-artifacts-prod"
    s3_bucket_knowledge: str = "vqms-knowledge-artifacts-prod"

    # --- SQS ---
    sqs_queue_prefix: str = "vqms-"
    sqs_max_receive_count: int = 3
    sqs_visibility_timeout: int = 300

    # --- EventBridge ---
    eventbridge_bus_name: str = "vqms-events"
    eventbridge_source: str = "vqms.pipeline"

    # --- Agent Config ---
    agent_confidence_threshold: float = 0.75
    agent_max_hops: int = 4
    agent_budget_max_tokens_in: int = 8000
    agent_budget_max_tokens_out: int = 4096
    agent_budget_currency_limit_usd: float = 0.50

    # --- SLA ---
    sla_warning_threshold_percent: int = 70
    sla_l1_escalation_threshold_percent: int = 85
    sla_l2_escalation_threshold_percent: int = 95
    sla_default_hours: int = 24

    # ----------------------------------------------------------------
    # Factory methods — build the frozen Config dataclasses
    # ----------------------------------------------------------------

    def s3_config(self) -> S3Config:
        """Build S3Config from settings."""
        return S3Config(region=self.aws_region)

    def sqs_config(self) -> SQSConfig:
        """Build SQSConfig from settings."""
        return SQSConfig(
            region=self.aws_region,
            max_receive_count=self.sqs_max_receive_count,
            visibility_timeout_seconds=self.sqs_visibility_timeout,
        )

    def eventbridge_config(self) -> EventBridgeConfig:
        """Build EventBridgeConfig from settings."""
        return EventBridgeConfig(
            event_bus_name=self.eventbridge_bus_name,
            source=self.eventbridge_source,
            region=self.aws_region,
        )

    def graph_api_config(self) -> GraphAPIConfig:
        """Build GraphAPIConfig from settings."""
        return GraphAPIConfig(
            tenant_id=self.graph_api_tenant_id,
            client_id=self.graph_api_client_id,
            client_secret=self.graph_api_client_secret,
            access_token=self.graph_api_access_token,
            mailbox_id=self.graph_api_mailbox,
        )

    def database_config(self) -> DatabaseConfig:
        """Build DatabaseConfig from settings."""
        return DatabaseConfig(
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            user=self.postgres_user,
            min_connections=self.postgres_pool_min,
            max_connections=self.postgres_pool_max,
        )

    def redis_config(self) -> RedisConfig:
        """Build RedisConfig from settings."""
        return RedisConfig(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            db=self.redis_db,
            ssl=self.redis_ssl,
        )

    def bedrock_config(self) -> BedrockConfig:
        """Build BedrockConfig from settings."""
        return BedrockConfig(
            region=self.bedrock_region,
            primary_model_id=self.bedrock_model_id,
            fallback_model_id=self.bedrock_fallback_model_id,
            max_retries=self.bedrock_max_retries,
            default_temperature=self.bedrock_temperature,
        )

    def salesforce_config(self) -> SalesforceConfig:
        """Build SalesforceConfig from settings."""
        return SalesforceConfig(
            instance_url=self.salesforce_instance_url,
        )

    def servicenow_config(self) -> ServiceNowConfig:
        """Build ServiceNowConfig from settings."""
        return ServiceNowConfig(
            instance_url=self.servicenow_instance_url,
        )


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance.

    First call reads .env and environment variables.
    Subsequent calls return the same object.
    """
    return Settings()
