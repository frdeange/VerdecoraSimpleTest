from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient, ContainerSasPermissions, generate_container_sas

from src.config.security import get_managed_identity_credential
from src.upload_web.config import UploadWebSettings, get_settings
from src.upload_web.models.upload import UploadSession

_UPLOAD_SESSIONS: dict[str, UploadSession] = {}
logger = logging.getLogger(__name__)


def create_upload_session(
    user_oid: str,
    user_name: str,
    settings: UploadWebSettings | None = None,
) -> UploadSession:
    resolved_settings = settings or get_settings()
    session_id = str(uuid4())
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(hours=1)
    session = UploadSession(
        session_id=session_id,
        user_oid=user_oid,
        user_name=user_name,
        created_at=created_at,
        updated_at=created_at,
        status="created",
        files=[],
        container_name=resolved_settings.raw_blob_container,
        upload_prefix=_build_upload_prefix(session_id),
        sas_token=_generate_upload_sas(session_id, resolved_settings, expires_at),
        sas_expires_at=expires_at,
    )
    _UPLOAD_SESSIONS[session_id] = session
    container = _resolve_upload_sessions_container(resolved_settings)
    if container is not None:
        try:
            container.create_item(_to_document(session))
        except Exception:
            logger.warning("Cosmos upload-session create failed; using in-memory fallback.", exc_info=True)
    return session


def get_upload_session(session_id: str, settings: UploadWebSettings | None = None) -> UploadSession | None:
    resolved_settings = settings or get_settings()
    session = _UPLOAD_SESSIONS.get(session_id)
    if session is None:
        container = _resolve_upload_sessions_container(resolved_settings)
        if container is None:
            return None
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.id = @session_id",
                parameters=[{"name": "@session_id", "value": session_id}],
                enable_cross_partition_query=True,
            )
            document = next(iter(items), None)
            if document is None:
                return None
            session = _from_document(document)
            _UPLOAD_SESSIONS[session_id] = session
        except Exception:
            logger.warning("Cosmos upload-session read failed; using in-memory fallback.", exc_info=True)
            return _UPLOAD_SESSIONS.get(session_id)

    return _sync_processing_status(session, resolved_settings)


def update_upload_session(
    session: UploadSession,
    settings: UploadWebSettings | None = None,
) -> UploadSession:
    resolved_settings = settings or get_settings()
    session.updated_at = datetime.now(UTC)
    _UPLOAD_SESSIONS[session.session_id] = session
    container = _resolve_upload_sessions_container(resolved_settings)
    if container is not None:
        try:
            container.upsert_item(_to_document(session))
        except Exception:
            logger.warning("Cosmos upload-session upsert failed; using in-memory fallback.", exc_info=True)
    return session


def get_all_user_sessions(user_oid: str, settings: UploadWebSettings | None = None) -> list[UploadSession]:
    """Return all sessions belonging to the given user."""
    resolved_settings = settings or get_settings()
    sessions: list[UploadSession] = []
    container = _resolve_upload_sessions_container(resolved_settings)
    if container is not None:
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.user_oid = @user_oid",
                parameters=[{"name": "@user_oid", "value": user_oid}],
                partition_key=user_oid,
            )
            sessions = [_from_document(item) for item in items]
            for session in sessions:
                _UPLOAD_SESSIONS[session.session_id] = session
        except Exception:
            logger.warning("Cosmos upload-session query failed; using in-memory fallback.", exc_info=True)
            sessions = [session for session in _UPLOAD_SESSIONS.values() if session.user_oid == user_oid]
    else:
        sessions = [session for session in _UPLOAD_SESSIONS.values() if session.user_oid == user_oid]

    synced_sessions = [_sync_processing_status(session, resolved_settings) for session in sessions]
    return sorted(synced_sessions, key=_session_sort_key, reverse=True)


def clear_upload_sessions() -> None:
    _UPLOAD_SESSIONS.clear()
    _get_database_client.cache_clear()


def _build_upload_prefix(session_id: str) -> str:
    return f"{session_id}/"


def _generate_upload_sas(session_id: str, settings: UploadWebSettings, expiry: datetime) -> str:
    account_url = os.getenv("STORAGE_ACCOUNT_URL") or os.getenv("BLOB_ACCOUNT")
    if not account_url:
        return _build_mock_sas_token(session_id, expiry)

    credential = get_managed_identity_credential()
    blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
    start_time = datetime.now(UTC) - timedelta(minutes=5)
    delegation_key = blob_service_client.get_user_delegation_key(start_time, expiry)
    permissions = ContainerSasPermissions(read=True, write=True, create=True)
    sas_token = generate_container_sas(
        account_name=blob_service_client.account_name,
        container_name=settings.raw_blob_container,
        user_delegation_key=delegation_key,
        permission=permissions,
        start=start_time,
        expiry=expiry,
        protocol="https",
    )
    return sas_token


def _build_mock_sas_token(session_id: str, expiry: datetime) -> str:
    safe_expiry = expiry.isoformat().replace("+00:00", "Z")
    return f"mock-sas-session={session_id}&prefix={_build_upload_prefix(session_id)}&exp={safe_expiry}"


@lru_cache(maxsize=4)
def _get_database_client(cosmos_url: str, database_name: str) -> Any:
    client = CosmosClient(url=cosmos_url, credential=get_managed_identity_credential())
    return client.get_database_client(database_name)


def _get_upload_sessions_container(settings: UploadWebSettings) -> Any:
    if not _cosmos_is_configured():
        return None
    return _get_database_client(settings.cosmos_url, settings.cosmos_database).get_container_client(
        settings.upload_sessions_container
    )


def _get_processing_records_container(settings: UploadWebSettings) -> Any:
    if not _cosmos_is_configured():
        return None
    return _get_database_client(settings.cosmos_url, settings.cosmos_database).get_container_client(
        settings.processing_records_container
    )


def _to_document(session: UploadSession) -> dict[str, Any]:
    document = session.model_dump(mode="json")
    document["id"] = session.session_id
    return document


def _from_document(document: dict[str, Any]) -> UploadSession:
    payload = dict(document)
    payload["session_id"] = str(payload.get("session_id") or payload.get("id") or "")
    payload.pop("id", None)
    return UploadSession.model_validate(payload)


def _extract_blob_path(record: dict[str, Any]) -> str | None:
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        blob_path = metadata.get("blob_path")
        if blob_path:
            return str(blob_path)

    blob_url = record.get("blob_url")
    if not blob_url:
        return None
    parsed = urlparse(str(blob_url))
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        return None
    return "/".join(path_parts[1:])


def _normalize_processing_status(status: str | None) -> str | None:
    normalized = str(status or "").strip().lower()
    if not normalized:
        return None
    if normalized in {
        "created",
        "uploading",
        "preflight",
        "confirmed",
        "processing",
        "hitl_pending",
        "completed",
        "rejected",
        "failed",
    }:
        return normalized
    if normalized in {"queued", "pending"}:
        return "processing"
    if normalized in {"error"}:
        return "failed"
    return normalized


def _aggregate_status(current_status: str, file_statuses: list[str]) -> str:
    normalized = [status for status in file_statuses if status]
    if not normalized:
        return current_status
    if any(status == "processing" for status in normalized):
        return "processing"
    if any(status == "hitl_pending" for status in normalized):
        return "hitl_pending"
    if any(status == "failed" for status in normalized):
        return "failed"
    if any(status == "rejected" for status in normalized):
        return "rejected"
    if all(status == "completed" for status in normalized):
        return "completed"
    if any(status in {"completed", "rejected"} for status in normalized):
        return "processing"
    return current_status


def _sync_processing_status(session: UploadSession, settings: UploadWebSettings) -> UploadSession:
    processing_records = _get_processing_records(session, settings)
    if not processing_records:
        return session

    file_statuses, status_by_blob_path = _build_processing_status_maps(processing_records)
    changed = _apply_file_processing_statuses(session, status_by_blob_path)
    aggregate_status = _aggregate_status(session.status, file_statuses)
    if aggregate_status != session.status:
        session.status = aggregate_status
        changed = True

    if changed:
        update_upload_session(session, settings)

    return session


def _session_sort_key(session: UploadSession) -> datetime:
    latest_file_upload = max((upload_file.uploaded_at for upload_file in session.files), default=session.updated_at)
    return max(_ensure_utc(session.updated_at), _ensure_utc(latest_file_upload))


def _get_processing_records(session: UploadSession, settings: UploadWebSettings) -> list[dict[str, Any]]:
    container = _resolve_processing_records_container(settings)
    if container is None:
        return []

    try:
        items = container.query_items(
            query=(
                "SELECT * FROM c WHERE c.upload_session_id = @session_id "
                "AND c.uploader_oid = @user_oid"
            ),
            parameters=[
                {"name": "@session_id", "value": session.session_id},
                {"name": "@user_oid", "value": session.user_oid},
            ],
            enable_cross_partition_query=True,
        )
    except Exception:
        logger.warning("Cosmos processing-record query failed; keeping cached upload-session status.", exc_info=True)
        return []

    return list(items)


def _build_processing_status_maps(processing_records: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    file_statuses: list[str] = []
    status_by_blob_path: dict[str, str] = {}
    for record in processing_records:
        normalized_status = _normalize_processing_status(record.get("status"))
        if not normalized_status:
            continue
        file_statuses.append(normalized_status)
        blob_path = _extract_blob_path(record)
        if blob_path:
            status_by_blob_path[blob_path] = normalized_status
    return file_statuses, status_by_blob_path


def _apply_file_processing_statuses(session: UploadSession, status_by_blob_path: dict[str, str]) -> bool:
    changed = False
    for upload_file in session.files:
        file_status = status_by_blob_path.get(upload_file.blob_path)
        if file_status and upload_file.processing_status != file_status:
            upload_file.processing_status = file_status
            changed = True
    return changed


def _cosmos_is_configured() -> bool:
    return bool(os.getenv("COSMOS_ENDPOINT") or os.getenv("COSMOS_URL"))


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _resolve_upload_sessions_container(settings: UploadWebSettings) -> Any:
    try:
        return _get_upload_sessions_container(settings)
    except Exception:
        logger.warning("Cosmos upload-session container unavailable; using in-memory fallback.", exc_info=True)
        return None


def _resolve_processing_records_container(settings: UploadWebSettings) -> Any:
    try:
        return _get_processing_records_container(settings)
    except Exception:
        logger.warning("Cosmos processing-record container unavailable; keeping cached upload-session status.", exc_info=True)
        return None


__all__ = [
    "clear_upload_sessions",
    "create_upload_session",
    "get_all_user_sessions",
    "get_upload_session",
    "update_upload_session",
]
