from __future__ import annotations

import logging

from src.services.orchestrator.main import configure_logging


def test_configure_logging_sets_root_logger_level(monkeypatch: object) -> None:
    root_logger = logging.getLogger()
    original_level = root_logger.level
    try:
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        root_logger.setLevel(logging.WARNING)

        configure_logging()

        assert root_logger.level == logging.INFO
    finally:
        root_logger.setLevel(original_level)
