from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class UploadWebSettings(BaseSettings):
    """Runtime settings for the Upload Web application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    blob_account: str = Field(
        default="https://storage.example.com",
        validation_alias=AliasChoices("BLOB_ACCOUNT", "STORAGE_ACCOUNT_URL"),
    )
    cosmos_url: str = Field(
        default="https://localhost:8081",
        validation_alias=AliasChoices("COSMOS_URL", "COSMOS_ENDPOINT"),
    )
    app_insights_connection_string: str = Field(
        default="",
        validation_alias=AliasChoices("APP_INSIGHTS_CONNECTION_STRING", "APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )
    raw_blob_container: str = Field(default="albaranes-raw", validation_alias=AliasChoices("RAW_BLOB_CONTAINER"))
    upload_sessions_container: str = Field(
        default="upload-sessions",
        validation_alias=AliasChoices("UPLOAD_SESSIONS_CONTAINER"),
    )
    azure_tenant_id: str = Field(default="", validation_alias=AliasChoices("AZURE_TENANT_ID"))
    key_vault_url: str = Field(default="", validation_alias=AliasChoices("KEY_VAULT_URL"))
    docintell_endpoint: str = Field(default="", validation_alias=AliasChoices("DOCINTELL_ENDPOINT"))
    servicebus_namespace: str = Field(
        default="",
        validation_alias=AliasChoices("SERVICEBUS_FQ_NAMESPACE", "SERVICEBUS_NAMESPACE"),
    )
    extraction_queue_name: str = Field(
        default="extraccion-queue",
        validation_alias=AliasChoices("SERVICEBUS_EXTRACTION_QUEUE", "EXTRACTION_QUEUE_NAME"),
    )
    cosmos_database: str = Field(
        default="verdecora",
        validation_alias=AliasChoices("COSMOS_DATABASE"),
    )
    session_signing_key: str = Field(
        default="dev-only-upload-web-session-signing-key-change-me",
        validation_alias=AliasChoices("SESSION_SIGNING_KEY"),
    )
    allowed_uploader_group: str = Field(
        default="verdecora-store-uploaders",
        validation_alias=AliasChoices("UPLOAD_ALLOWED_GROUP"),
    )
    public_origin: str = Field(
        default="",
        validation_alias=AliasChoices("UPLOAD_WEB_PUBLIC_ORIGIN", "UPLOAD_WEB_PUBLIC_BASE_URL", "PUBLIC_ORIGIN"),
    )

    @property
    def normalized_public_origin(self) -> str:
        raw_value = self.public_origin.strip()
        if not raw_value:
            return ""
        if "://" not in raw_value:
            raw_value = f"https://{raw_value}"
        parsed = urlsplit(raw_value)
        if not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def build_public_url(self, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        if not self.normalized_public_origin:
            return normalized_path
        return f"{self.normalized_public_origin}{normalized_path}"


@lru_cache(maxsize=1)
def get_settings() -> UploadWebSettings:
    return UploadWebSettings()
