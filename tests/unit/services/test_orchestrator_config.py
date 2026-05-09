from __future__ import annotations

from src.services.orchestrator.config import OrchestratorConfig


def test_orchestrator_config_defaults_ai_project_endpoint_to_empty_string(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)

    config = OrchestratorConfig()

    assert config.azure_ai_project_endpoint == ""
