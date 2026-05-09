from __future__ import annotations

import json

from src.services.orchestrator.handler import deserialize_message


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
