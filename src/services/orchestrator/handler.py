from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.services.flow0_dedup.dedup_handler import parse_event_grid_payload
from src.services.flow0_dedup.models import ForwardedExtractionMessage

from .orchestration import OrchestrationError, OrchestrationRequest, OrchestrationResult, OrchestratorService

LOGGER = logging.getLogger(__name__)


class QueueMessageError(ValueError):
    """Raised when a Service Bus payload cannot be converted into an orchestration request."""


def _extract_store_id(blob_path: str) -> str:
    segments = [segment for segment in blob_path.split("/") if segment]
    return segments[3] if len(segments) >= 4 else "unknown-store"


def _request_from_event_grid_payload(payload: Any) -> OrchestrationRequest:
    event = parse_event_grid_payload(payload)
    metadata = {
        "blob_path": event.blob_path,
        "blob_name": event.blob_name,
        "blob_etag": event.data.eTag,
        "store_id": _extract_store_id(event.blob_path),
        "event_id": event.id,
        "event_type": event.eventType,
        "event_time": event.eventTime.isoformat(),
        "content_type": event.data.contentType,
        "content_length": event.data.contentLength,
        "blob_metadata": event.data.metadata,
        "subject": event.subject,
    }
    metadata.update({key: value for key, value in event.data.metadata.items() if key not in metadata})
    return OrchestrationRequest(
        processing_id=event.id,
        blob_url=event.blob_url,
        metadata=metadata,
    )


def _extract_message_body(message: Any) -> Any:
    if hasattr(message, "body"):
        return b"".join(bytes(part) for part in message.body)
    return message


def _deserialize_payload(body: Any) -> Any:
    if isinstance(body, bytes):
        return json.loads(body.decode("utf-8"))
    if isinstance(body, str):
        return json.loads(body)
    return body


def _try_event_grid_request(payload: Any) -> OrchestrationRequest | None:
    if isinstance(payload, list):
        try:
            return _request_from_event_grid_payload(payload)
        except Exception:
            return None

    if isinstance(payload, dict) and {"id", "eventType", "data"}.issubset(payload):
        try:
            return _request_from_event_grid_payload(payload)
        except Exception:
            return None

    return None


def _request_from_forwarded_message(payload: Any) -> OrchestrationRequest:
    forwarded = ForwardedExtractionMessage.model_validate(payload)
    metadata = dict(forwarded.metadata)
    metadata.update(
        {
            "dedup_key": forwarded.dedup_key,
            "blob_path": forwarded.blob_path,
            "blob_name": forwarded.blob_name,
            "blob_etag": forwarded.blob_etag,
            "store_id": forwarded.store_id,
            "event_id": forwarded.event_id,
            "event_time": forwarded.event_time.isoformat(),
        }
    )
    if forwarded.upload_session_id:
        metadata["upload_session_id"] = forwarded.upload_session_id
    if forwarded.uploader_oid:
        metadata["uploader_oid"] = forwarded.uploader_oid
    if forwarded.uploader_name:
        metadata["uploader_name"] = forwarded.uploader_name
    return OrchestrationRequest(
        processing_id=forwarded.albaran_id,
        blob_url=forwarded.blob_url,
        metadata=metadata,
    )


def _try_upload_session_request(payload: Any) -> OrchestrationRequest | None:
    if not isinstance(payload, dict):
        return None

    session_id = payload.get("session_id")
    files = payload.get("files")
    if not isinstance(session_id, str) or not session_id or not isinstance(files, list) or not files:
        return None

    first_file = files[0]
    if not isinstance(first_file, dict):
        return None

    blob_url = first_file.get("blob_url")
    if not isinstance(blob_url, str) or not blob_url:
        return None

    metadata = {
        "session_id": session_id,
        "upload_session_id": session_id,
        "user_oid": payload.get("user_oid"),
        "uploader_oid": payload.get("user_oid"),
        "user_name": payload.get("user_name"),
        "uploader_name": payload.get("user_name"),
        "timestamp": payload.get("timestamp"),
        "confirmed_at": payload.get("confirmed_at"),
        "preflight": payload.get("preflight"),
        "files": files,
        "primary_file": first_file,
        "blob_path": first_file.get("blob_path"),
        "blob_name": first_file.get("filename"),
        "content_type": first_file.get("content_type"),
        "content_length": first_file.get("size_bytes"),
    }
    return OrchestrationRequest(
        processing_id=session_id,
        blob_url=blob_url,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


def deserialize_message(message: Any) -> OrchestrationRequest:
    payload = _deserialize_payload(_extract_message_body(message))

    if event_grid_request := _try_event_grid_request(payload):
        return event_grid_request

    if isinstance(payload, dict) and "albaran_id" in payload:
        try:
            return _request_from_forwarded_message(payload)
        except Exception as exc:  # pragma: no cover - defensive parsing path.
            raise QueueMessageError("Invalid Service Bus payload for orchestration.") from exc

    if upload_session_request := _try_upload_session_request(payload):
        return upload_session_request

    try:
        return OrchestrationRequest.model_validate(payload)
    except Exception:
        try:
            return _request_from_forwarded_message(payload)
        except Exception as exc:  # pragma: no cover - defensive parsing path.
            raise QueueMessageError("Invalid Service Bus payload for orchestration.") from exc


async def handle_message(
    orchestrator: OrchestratorService,
    *,
    receiver: Any,
    message: Any,
) -> OrchestrationResult:
    request = deserialize_message(message)
    try:
        result = await orchestrator.process_document(request)
    except OrchestrationError as exc:
        error_description = exc.result.error or str(exc)
        LOGGER.exception(
            "Message processing failed: processing_id=%s delivery_count=%s dead_letter=%s error=%s",
            exc.result.processing_id,
            getattr(message, "delivery_count", 1),
            getattr(message, "delivery_count", 1) >= orchestrator.config.max_delivery_attempts,
            error_description,
        )
        if getattr(message, "delivery_count", 1) >= orchestrator.config.max_delivery_attempts:
            await receiver.dead_letter_message(
                message,
                reason="orchestration_failed",
                error_description=error_description,
            )
        else:
            await receiver.abandon_message(message)
        return exc.result

    await receiver.complete_message(message)
    return result


async def consume_extraction_queue(orchestrator: OrchestratorService, *, max_wait_time: int = 5) -> int:
    service_bus_client = orchestrator.dependencies.get_service_bus_client()
    async with service_bus_client.get_queue_receiver(queue_name=orchestrator.config.extraction_queue_name) as receiver:
        messages = await receiver.receive_messages(
            max_message_count=orchestrator.config.max_receive_batch_size,
            max_wait_time=max_wait_time,
        )
        for message in messages:
            await handle_message(orchestrator, receiver=receiver, message=message)
        return len(messages)


async def run_queue_consumer(orchestrator: OrchestratorService, stop_event: asyncio.Event) -> None:
    import logging as _logging

    _log = _logging.getLogger(__name__)
    _log.info(
        "Queue consumer starting: namespace=%s queue=%s poll_interval=%ss",
        orchestrator.config.service_bus_fully_qualified_namespace,
        orchestrator.config.extraction_queue_name,
        orchestrator.config.service_bus_poll_interval_seconds,
    )
    while not stop_event.is_set():
        try:
            received = await consume_extraction_queue(orchestrator)
            if received > 0:
                _log.info("Processed %d message(s) from %s", received, orchestrator.config.extraction_queue_name)
                continue
        except asyncio.CancelledError:
            break
        except Exception:
            _log.exception("Queue consumer error — retrying in %ss", orchestrator.config.service_bus_poll_interval_seconds)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=orchestrator.config.service_bus_poll_interval_seconds)
        except TimeoutError:
            continue
    _log.info("Queue consumer stopped")
