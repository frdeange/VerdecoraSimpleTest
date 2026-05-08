# Infrastructure Validation Report

- **Validated at:** 2026-05-08T15:17:35.1978815+02:00
- **Azure resource group:** `rg-verdecora-simple-dev`
- **Validator:** Lambert 🧪

## Results

| Check | Status | Notes |
| --- | --- | --- |
| Resource group inventory | ✅ | 24 resources found (including child resources), with all expected shared services present: Storage, Cosmos DB, Service Bus, Key Vault, ACR, AI Services, Log Analytics, App Insights, Event Grid, and the Container Apps environment. |
| Storage account | ✅ | `stvdsdev4vtapr` is `available`, `publicNetworkAccess=Enabled`, and containers `albaranes-raw`, `albaranes-processed`, and `dlq` exist. |
| Cosmos DB | ✅ | `cosmos-vds-dev-4vtapr` is `Succeeded`, `publicNetworkAccess=Enabled`, and SQL database `albaranes-db` exists. |
| Service Bus | ✅ | `sb-vds-dev-4vtapr` is `Active`, `publicNetworkAccess=Enabled`, queues `extraccion-in` / `extraccion-queue` exist, and topics `albaran-events` / `hitl-decisions` exist. |
| Key Vault | ✅ | `kv-vds-dev-4vtapr` is reachable and has `publicNetworkAccess=Enabled`. |
| Azure Container Registry | ✅ | `acrvdsdev4vtapr` is `Succeeded`, `publicNetworkAccess=Enabled`, and `az acr login --expose-token` returned the expected login server. `az acr check-health` also reached the registry challenge endpoint, but the local CLI hit a Docker/CLI traceback after the connectivity checks. |
| AI Services | ✅ | `vds-docintell-dev-4vtapr` (Form Recognizer) and `vds-ais-dev-4vtapr` (AI Services) are both `Succeeded` with public network access enabled. |
| Container Apps environment | ✅ | Managed environment `acae-verdecora-dev` exists in Sweden Central. |
| Container Apps deployment | ❌ | `az containerapp list` returned an empty array: no Container Apps are currently deployed in the environment. |
| Event Grid | ✅ | System topic `eg-st-albaranes-dev` exists and is `Succeeded`. |
| Log Analytics | ✅ | Workspace `log-albaranes-dev` is `Succeeded` with ingestion/query public access enabled. |
| Application Insights | ✅ | Component `appi-albaranes-dev` is `Succeeded`, connected to Log Analytics, and has public ingestion/query access enabled. The requested `az monitor app-insights component list` command was not supported by the installed CLI, so validation was completed with `az monitor app-insights component show`. |
| Managed identity / RBAC check | ❌ | No Container Apps are deployed, so there are no workload identities to validate. |

## Issues Found

1. **No Container Apps deployed** — the infrastructure includes a Container Apps environment, but no actual Container Apps workloads are present.
2. **Managed identity validation blocked** — because there are no Container Apps, workload identity assignment could not be verified.
3. **Azure CLI command mismatch for App Insights** — `az monitor app-insights component list` was not available in the installed CLI, although `show` works.
4. **`az acr check-health` local tooling issue** — network and token checks passed, but the command raised a Docker/CLI traceback afterward on this workstation.

## Overall Assessment

**Partial pass.** Shared Azure platform services are deployed, healthy, publicly reachable, and expose the expected child resources. The validation did **not** fully pass end-to-end because the application workload layer is incomplete: no Container Apps are deployed, so workload reachability and managed identity/RBAC validation cannot be completed yet.
