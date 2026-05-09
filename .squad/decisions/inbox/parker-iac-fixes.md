# Parker IaC fixes — Issues #92, #93, #97

- **Date:** 2026-05-10
- **Branch:** `squad/92-97-iac-fixes`
- **Decision:** Keep Azure AI Foundry wiring explicit across modules: pass both AI Services account name and AI Project name from `ai-foundry.bicep` through `main.bicep`, compose the project endpoint in `container-apps.bicep`, and grant the orchestrator the required RBAC roles at both the account and project scopes in `identity.bicep`.
- **Why:** The orchestrator now depends on the Azure AI Project endpoint and project-scoped permissions, so hiding the project name behind a prebuilt endpoint string would make RBAC and runtime configuration drift easier.
- **Issue #93 note:** AI model deployment names must stay identical to the deployed model names. `ai-foundry.bicep` now uses shared model-name variables for both deployment resource names and `properties.model.name` so aliases cannot silently diverge.
- **Runtime config:** `AZURE_AI_PROJECT_ENDPOINT` defaults are now empty in Python config, making the deployment-provided environment variable the source of truth.
- **Validation:** `az bicep build --file infra/modules/main.bicep`; `python -m pytest tests\unit\test_config_agents.py tests\unit\test_agents_pipeline.py tests\unit\test_agent_factory.py tests\unit\services\test_orchestrator_config.py`
