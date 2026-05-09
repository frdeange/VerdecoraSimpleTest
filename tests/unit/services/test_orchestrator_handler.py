from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.services.orchestrator.handler import deserialize_message, handle_message
from src.services.orchestrator.orchestration import OrchestrationError, OrchestrationResult


def test_deserialize_message_accepts_upload_session_payload() -> None:
    payload = {
        "session_id": "session-123",
        "user_oid": "user-456",
        "user_name": "Kiko de Angel",
        "timestamp": "2026-05-09T11:00:00+00:00",
        "confirmed_at": "2026-05-09T11:00:00+00:00",
        "files": [
            {
                "filename": "ticket.pdf",
                "blob_path": "uploads/session-123/ticket.pdf",
                "blob_url": "https://storage.example/uploads/session-123/ticket.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
            },
            {
                "filename": "ticket-page-2.pdf",
                "blob_path": "uploads/session-123/ticket-page-2.pdf",
                "blob_url": "https://storage.example/uploads/session-123/ticket-page-2.pdf",
                "content_type": "application/pdf",
                "size_bytes": 2048,
            },
        ],
        "preflight": {
            "is_albaran": True,
            "confidence": 1.0,
            "supplier_name": "Proveedor Demo",
        },
    }

    request = deserialize_message(json.dumps(payload))

    assert request.processing_id == "session-123"
    assert request.blob_url == "https://storage.example/uploads/session-123/ticket.pdf"
    assert request.metadata["session_id"] == "session-123"
    assert request.metadata["upload_session_id"] == "session-123"
    assert request.metadata["user_oid"] == "user-456"
    assert request.metadata["uploader_oid"] == "user-456"
    assert request.metadata["user_name"] == "Kiko de Angel"
    assert request.metadata["uploader_name"] == "Kiko de Angel"
    assert request.metadata["preflight"] == payload["preflight"]
    assert request.metadata["files"] == payload["files"]
    assert request.metadata["primary_file"] == payload["files"][0]


class FakeReceiver:
    def __init__(self) -> None:
        self.completed_messages: list[object] = []
        self.abandoned_messages: list[object] = []
        self.dead_lettered_messages: list[dict[str, str]] = []

    async def complete_message(self, message: object) -> None:
        self.completed_messages.append(message)

    async def abandon_message(self, message: object) -> None:
        self.abandoned_messages.append(message)

    async def dead_letter_message(self, message: object, *, reason: str, error_description: str) -> None:
        self.dead_lettered_messages.append({"reason": reason, "error_description": error_description})


class FakeMessage:
    def __init__(self, payload: dict[str, object], *, delivery_count: int = 1) -> None:
        self.body = [json.dumps(payload).encode("utf-8")]
        self.delivery_count = delivery_count


@pytest.mark.asyncio
async def test_handle_message_dead_letters_with_underlying_error() -> None:
    result = OrchestrationResult(
        processing_id="session-123",
        blob_url="https://storage.example/uploads/session-123/ticket.pdf",
        status="failed",
        routing_decision="failed",
        error="analyze_document: document intelligence offline",
    )

    class FakeOrchestrator:
        config = SimpleNamespace(max_delivery_attempts=5)

        async def process_document(self, request: object) -> object:
            raise OrchestrationError("Processing failed", result=result)

    receiver = FakeReceiver()
    message = FakeMessage(
        {
            "processing_id": "session-123",
            "blob_url": "https://storage.example/uploads/session-123/ticket.pdf",
            "metadata": {},
        },
        delivery_count=5,
    )

    outcome = await handle_message(FakeOrchestrator(), receiver=receiver, message=message)

    assert outcome.error == "analyze_document: document intelligence offline"
    assert receiver.dead_lettered_messages == [
        {
            "reason": "orchestration_failed",
            "error_description": "analyze_document: document intelligence offline",
        }
    ]
