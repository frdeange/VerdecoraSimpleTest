from __future__ import annotations

import json
from typing import Any

from src.services.flow0_dedup.dedup_handler import (
    Flow0DedupHandler,
    build_dedup_key,
    build_partition_key,
    parse_event_grid_payload,
)


class FakeCosmosContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def upsert_item(self, *, body: dict[str, Any]) -> dict[str, Any]:
        self.items[str(body["id"])] = dict(body)
        return dict(body)

    def query_items(self, *, parameters: list[dict[str, Any]], **_: Any) -> list[dict[str, Any]]:
        param_map = {p["name"]: p["value"] for p in parameters}
        dedup_key = param_map.get("@dedup_key")
        matches = [item for item in self.items.values() if item.get("dedup_key") == dedup_key]
        return matches[:1]


class FakeSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send_messages(self, message: Any) -> None:
        body = b"".join(bytes(part) for part in message.body)
        self.messages.append(json.loads(body.decode("utf-8")))


def test_parse_event_grid_payload_accepts_event_grid_arrays() -> None:
    event = parse_event_grid_payload(
        [
            {
                "id": "evt-1",
                "eventType": "Microsoft.Storage.BlobCreated",
                "subject": "/blobServices/default/containers/albaranes-raw/blobs/2026/05/tienda_007/test.pdf",
                "eventTime": "2026-05-04T08:12:33Z",
                "data": {
                    "eTag": "etag-1",
                    "url": "https://storage.blob.core.windows.net/albaranes-raw/2026/05/tienda_007/test.pdf",
                    "metadata": {"blob_hash": "abc123"},
                },
            }
        ]
    )

    assert event.id == "evt-1"
    assert event.blob_path == "albaranes-raw/2026/05/tienda_007/test.pdf"
    assert event.blob_name == "test.pdf"


def test_build_dedup_key_prefers_hash_then_etag_then_name_and_date() -> None:
    event = parse_event_grid_payload(
        {
            "id": "evt-2",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/albaranes-raw/blobs/2026/05/tienda_007/test.pdf",
            "eventTime": "2026-05-04T08:12:33Z",
            "data": {
                "eTag": "etag-2",
                "url": "https://storage.blob.core.windows.net/albaranes-raw/2026/05/tienda_007/test.pdf",
                "metadata": {"blob_hash": "hash-2"},
            },
        }
    )
    assert build_dedup_key(event) == "hash:hash-2"

    event_without_hash = event.model_copy(update={"data": event.data.model_copy(update={"metadata": {}})})
    assert build_dedup_key(event_without_hash) == "etag:etag-2"

    event_without_etag = event_without_hash.model_copy(update={"data": event.data.model_copy(update={"metadata": {}, "eTag": None})})
    assert build_dedup_key(event_without_etag) == "name-date:test.pdf:2026-05-04"


def test_build_partition_key_uses_store_and_year_month() -> None:
    event = parse_event_grid_payload(
        {
            "id": "evt-3",
            "eventType": "Microsoft.Storage.BlobCreated",
            "subject": "/blobServices/default/containers/albaranes-raw/blobs/2026/05/tienda_001/test.pdf",
            "eventTime": "2026-05-04T08:12:33Z",
            "data": {"url": "https://storage.blob.core.windows.net/albaranes-raw/2026/05/tienda_001/test.pdf"},
        }
    )

    assert build_partition_key("tienda_001", event.eventTime) == "tienda_001_2026_05"


def test_handle_message_accepts_upload_session_payloads() -> None:
    handler = Flow0DedupHandler(FakeCosmosContainer(), FakeSender())

    forwarded = handler.handle_message(
        {
            "session_id": "sess-001",
            "user_oid": "oid-001",
            "user_name": "Store User",
            "timestamp": "2026-05-09T00:00:00Z",
            "confirmed_at": "2026-05-09T00:00:00Z",
            "files": [
                {
                    "filename": "page1.pdf",
                    "blob_path": "sess-001/page1.pdf",
                    "blob_url": "https://acct.blob.core.windows.net/albaranes-raw/sess-001/page1.pdf",
                    "albaran_group": "alb-1",
                }
            ],
        }
    )

    assert forwarded is True
