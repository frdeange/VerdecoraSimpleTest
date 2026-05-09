from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator, cast

from fastapi import FastAPI, HTTPException, Request

from .config import OrchestratorConfig, get_orchestrator_config
from .handler import run_queue_consumer
from .health import router as health_router
from .hitl_consumer import run_hitl_decision_consumer
from .orchestration import OrchestrationError, OrchestrationRequest, OrchestratorService

LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


class ManualProcessRequest(OrchestrationRequest):
    pass


def configure_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Always ensure a stdout handler exists (Uvicorn may have added stderr-only handlers)
    has_stdout = any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
        for h in root_logger.handlers
    )
    if not has_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(handler)

    for handler in root_logger.handlers:
        handler.setLevel(log_level)


def create_app(config: OrchestratorConfig | None = None) -> FastAPI:
    configure_logging()
    resolved_config = config or get_orchestrator_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        orchestrator = OrchestratorService(config=resolved_config)
        stop_event = asyncio.Event()
        consumer_task: asyncio.Task[None] | None = None
        hitl_consumer_task: asyncio.Task[None] | None = None
        app.state.orchestrator = orchestrator
        app.state.consumer_stop_event = stop_event

        if resolved_config.service_bus_polling_enabled:
            consumer_task = asyncio.create_task(run_queue_consumer(orchestrator, stop_event))
            app.state.consumer_task = consumer_task
            hitl_consumer_task = asyncio.create_task(run_hitl_decision_consumer(orchestrator, stop_event))
            app.state.hitl_consumer_task = hitl_consumer_task

        try:
            yield
        finally:
            stop_event.set()
            for task in (consumer_task, hitl_consumer_task):
                if task is not None:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
            await orchestrator.close()

    app = FastAPI(title="Verdecora Agentic Orchestrator", lifespan=lifespan)
    app.include_router(health_router)

    @app.post("/process")
    async def process_document(payload: ManualProcessRequest, request: Request) -> dict[str, object]:
        orchestrator = cast(OrchestratorService, request.app.state.orchestrator)
        try:
            result = await orchestrator.process_document(payload)
        except OrchestrationError as exc:
            raise HTTPException(status_code=500, detail=exc.result.model_dump(mode="json")) from exc
        return result.model_dump(mode="json")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    configure_logging()
    uvicorn.run("src.services.orchestrator.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
