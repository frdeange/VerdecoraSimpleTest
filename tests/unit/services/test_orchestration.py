from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.orchestrator.config import OrchestratorConfig
from src.services.orchestrator.orchestration import OrchestrationError, OrchestrationRequest, OrchestratorService


class FakeContainer:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    async def upsert_item(self, body: dict[str, object]) -> dict[str, object]:
        self.items.append(body)
        return body


class FakeDependencies:
    def __init__(self) -> None:
        self.container = FakeContainer()

    async def get_processing_container(self) -> FakeContainer:
        return self.container

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_process_document_logs_steps_and_preserves_failure_details(caplog: pytest.LogCaptureFixture) -> None:
    service = OrchestratorService(config=OrchestratorConfig(service_bus_polling_enabled=False), agent_client=object())
    service.dependencies = FakeDependencies()
    service.download_blob = AsyncMock(return_value=b"%PDF-1.7 test")
    service.analyze_document = AsyncMock(side_effect=RuntimeError("document intelligence offline"))
    service.pipeline = SimpleNamespace(run=AsyncMock())

    request = OrchestrationRequest(blob_url="https://storage.example/doc.pdf", metadata={"upload_session_id": "session-1"})

    with caplog.at_level(logging.INFO):
        with pytest.raises(OrchestrationError) as exc_info:
            await service.process_document(request)

    assert "Downloading blob..." in caplog.text
    assert "Analyzing document..." in caplog.text
    assert "Running pipeline..." not in caplog.text
    assert exc_info.value.result.error == "analyze_document: document intelligence offline"
    assert any(record.exc_info for record in caplog.records if record.levelno >= logging.ERROR)


@pytest.mark.asyncio
async def test_process_document_logs_pipeline_step_on_success(caplog: pytest.LogCaptureFixture) -> None:
    service = OrchestratorService(config=OrchestratorConfig(service_bus_polling_enabled=False), agent_client=object())
    service.dependencies = FakeDependencies()
    service.download_blob = AsyncMock(return_value=b"%PDF-1.7 test")
    service.analyze_document = AsyncMock(return_value={"content": "hola", "page_count": 1, "tables": [], "key_value_pairs": []})
    service.pipeline = SimpleNamespace(
        run=AsyncMock(return_value=SimpleNamespace(routing_decision="extract", model_dump=lambda mode="json": {"ok": True}))
    )

    request = OrchestrationRequest(blob_url="https://storage.example/doc.pdf", metadata={})

    with caplog.at_level(logging.INFO):
        result = await service.process_document(request)

    assert result.status == "completed"
    assert result.routing_decision == "extract"
    assert "Downloading blob..." in caplog.text
    assert "Analyzing document..." in caplog.text
    assert "Running pipeline..." in caplog.text
    assert "Document processing completed" in caplog.text


def test_orchestrator_config_defaults_to_processing_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXTRACTION_QUEUE_NAME", raising=False)

    config = OrchestratorConfig()

    assert config.extraction_queue_name == "extraccion-in"


def test_build_pipeline_input_populates_readable_raw_text() -> None:
    service = OrchestratorService(config=OrchestratorConfig(service_bus_polling_enabled=False), agent_client=object())

    pipeline_input = service._build_pipeline_input(
        blob_url="https://storage.example/doc.pdf",
        metadata={},
        ocr_payload={
            "content": "ALBARÁN HERSTERA",
            "key_value_pairs": [{"key": "pedido", "value": "PO-2026-0456"}],
            "tables": [
                {
                    "row_count": 2,
                    "column_count": 2,
                    "cells": [
                        {"row_index": 0, "column_index": 0, "content": "Artículo"},
                        {"row_index": 0, "column_index": 1, "content": "Cantidad"},
                        {"row_index": 1, "column_index": 0, "content": "ABC-001"},
                        {"row_index": 1, "column_index": 1, "content": "3"},
                    ],
                }
            ],
        },
    )

    assert pipeline_input.raw_text is not None
    assert pipeline_input.raw_text.startswith("ALBARÁN HERSTERA")
    assert "- pedido: PO-2026-0456" in pipeline_input.raw_text
    assert "Artículo | Cantidad" in pipeline_input.raw_text
