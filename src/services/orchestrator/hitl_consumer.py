"""Consume HITL decisions from the hitl-decisions topic and resume the pipeline.

When a reviewer approves a document via the HITL webform, their decision is
published to the ``hitl-decisions`` Service Bus topic.  This consumer picks up
those decisions and:
  - **approve / modify** → resumes the pipeline at the inventory stage
  - **reject** → marks the record as rejected in Cosmos

Wired into the orchestrator lifespan so it runs as a background task alongside
the extraction queue consumer.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.models.communication import HITLDecision
from src.models.inventory import PostingResult
from src.services.hitl_webform.callbacks import HITLCallbackHandler

logger = logging.getLogger(__name__)

HITL_DECISIONS_SUBSCRIPTION = "orchestrator-hitl"
HITL_DECISIONS_TOPIC = "hitl-decisions"


class _CosmosReviewStore:
    """Minimal adapter that satisfies ``CallbackReviewStore`` using a Cosmos container."""

    def __init__(self, container: Any) -> None:
        self._container = container

    async def get_review_record(self, albaran_id: str) -> dict[str, Any] | None:
        query = "SELECT TOP 1 * FROM c WHERE c.id = @id"
        params: list[dict[str, Any]] = [{"name": "@id", "value": albaran_id}]
        items = [item async for item in self._container.query_items(query=query, parameters=params)]
        return dict(items[0]) if items else None

    async def upsert_item(self, document: dict[str, Any]) -> dict[str, Any]:
        await self._container.upsert_item(document)
        return document


async def _inventory_processor_stub(payload: dict[str, Any]) -> PostingResult:
    """Stub inventory processor — real BC posting via MCP tools.

    In a fully wired system the pipeline's inventory agent would be invoked
    here.  For now we return a success stub so the HITL loop can close.
    """
    logger.info("Inventory processor invoked for HITL-approved payload (stub)")
    return PostingResult(
        success=True,
        message="Inventory posting via HITL approval (stub — BC MCP integration pending full wiring).",
    )


async def run_hitl_decision_consumer(
    orchestrator: Any,
    stop_event: asyncio.Event,
    *,
    topic_name: str = HITL_DECISIONS_TOPIC,
    subscription_name: str = HITL_DECISIONS_SUBSCRIPTION,
) -> None:
    """Long-running task that consumes HITL decisions from Service Bus topic."""
    try:
        from azure.servicebus.aio import ServiceBusClient
    except ModuleNotFoundError:
        logger.warning("azure-servicebus not installed — HITL decision consumer disabled")
        return

    config = orchestrator.config
    sb_client = orchestrator.dependencies.get_service_bus_client()

    logger.info(
        "Starting HITL decision consumer on topic=%s subscription=%s",
        topic_name,
        subscription_name,
    )

    while not stop_event.is_set():
        try:
            async with sb_client.get_subscription_receiver(
                topic_name=topic_name,
                subscription_name=subscription_name,
                max_wait_time=5,
            ) as receiver:
                async for message in receiver:
                    if stop_event.is_set():
                        break
                    try:
                        body = json.loads(str(message))
                        decision = HITLDecision.model_validate(body)

                        container = await orchestrator.dependencies.get_processing_container()
                        store = _CosmosReviewStore(container)
                        handler = HITLCallbackHandler(
                            store,
                            inventory_processor=_inventory_processor_stub,
                        )

                        result = await handler.handle_decision(decision)
                        logger.info(
                            "HITL decision processed: albaran=%s decision=%s status=%s",
                            decision.albaran_id,
                            decision.decision,
                            result.get("status", "unknown"),
                        )
                        await receiver.complete_message(message)
                    except Exception:
                        logger.exception("Error processing HITL decision message")
                        await receiver.abandon_message(message)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("HITL decision consumer error — retrying in 10s")
            await asyncio.sleep(10)

    logger.info("HITL decision consumer stopped")
