# Squad Decisions

## Active Decisions

### Parker — Delete private network modules (Issue #1)
- **Date:** 2026-05-08
- **Decision:** Remove private-network-only composition from `infra/modules/main.bicep` and make subnet wiring optional in surviving Container Apps modules.
- **Why:** Keeps deployment graph valid for public-endpoint target without leaving `main.bicep` broken.
- **Impact:** `main.bicep` no longer deploys VNet, private endpoints, NAT, self-hosted runners, or Front Door.

### Parker — Public PaaS access (Issue #2)
- **Date:** 2026-05-08
- **Decision:** Re-open public network access on core PaaS modules using minimal Bicep changes.
- **Implementation:** Only change explicit network exposure from private/deny to public/allow.
- **Security kept:** Identity, RBAC, local-auth restrictions remain primary control plane protections.

### Parker — Simplify ACA environments (Issue #3)
- **Date:** 2026-05-08
- **Decision:** Container Apps managed environments should deploy publicly by default without delegated subnets or VNet configuration.
- **Rationale:** Removes unnecessary network prerequisites while preserving managed identity, ACR pulls, ingress, scale rules, jobs, and app settings.

### Parker — Deployment notes (Issue #6)
- Name collisions with legacy `verdecoratest` resources; use deterministic `verdecora-simple`-scoped names with short unique suffix.
- Infrastructure rollouts: `enableContainerAppWorkloads` defaults to `true`; placeholder MCR images keep ACA workloads deployable before real images exist in ACR.
- AI Foundry deployment: `enableModelDeployments` defaults to `false` due to policy/quota validation; enable after confirmation.

### Parker — Upload-web Easy Auth IaC (Issue #31)
- **Date:** 2026-05-08
- **Decision:** Co-locate the `authConfigs` child resource with `upload-web-app.bicep` and parameterize the Entra client secret as a secure Container App secret reference.
- **Why:** Keeps upload-web authentication reproducible in one module while avoiding repository-stored credentials.
- **Impact:** Future deployments can stage upload-web first, then enable Easy Auth by setting `enableUploadWebAuth=true` plus secure Entra client credentials on the same module deployment.

### Dallas — CI/CD Redesign (Issue #4)
- **Date:** 2026-05-08
- **Decision:** Adopt GitHub-hosted `ubuntu-latest` runners and GitHub OIDC federation for Azure deployments.
- **Why:** Removes deprecated self-hosted setup; aligns with GitHub-native OIDC.
- **Consequence:** Repository variables must include `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `ACR_NAME`, `ENVIRONMENT`.

### Ash — Upload-web public endpoint config
- Upload-web treats public host as configuration: use `UPLOAD_WEB_PUBLIC_ORIGIN`.
- HITL callback fallback: `HITL_WEBFORM_BASE_URL` for final public webform host.
- Blob CORS: Allow exact upload-web origin only (ACA hostname or custom domain).

### Burke — BCToolBase `__name__` and `__doc__` for MAF compatibility (Issue #82)
- **Date:** 2026-05-09
- **Decision:** Any class that wraps a BC MCP operation must set `self.__name__` and `self.__doc__` inside `__init__()` in addition to standard attributes.
- **Why:** `agent_framework.normalize_tools()` derives tool name from `callable.__name__`; without this fix, all BC tools silently registered as `"unknown_function"`.
- **Impact:** PR #85 includes regression test `test_bc_tools_normalize_with_unique_agent_framework_names`.

### Dallas — GitHub OIDC Bootstrap Automation (CI/CD)
- **Date:** 2026-05-08
- **Decision:** Standardize Azure OIDC bootstrap in `scripts/setup-github-oidc.ps1` with auto-discovery of subscription and ACR.
- **Pattern:** Make idempotent for app registration, service principal, federated credentials, and RBAC assignments.
- **Validation:** Verified for `frdeange/VerdecoraSimpleTest` with `rg-verdecora-simple-dev`.

### Dallas — OIDC RBAC Scope for Subscription Deployments
- **Date:** 2026-05-08
- **Decision:** Grant GitHub OIDC service principal `Contributor` at subscription scope (not just resource group scope). Keep `AcrPush` scoped to discovered ACR.
- **Why:** Subscription-scoped deployments require `Microsoft.Resources/deployments/validate/action` before resource group exists.
- **Implementation:** Update `scripts/setup-github-oidc.ps1` and `scripts/README.md`.

### Dallas — Smart Path-Filtered CI/CD Split
- **Date:** 2026-05-08
- **Decision:** Split into dedicated `deploy-infra.yml` and redesign `build-deploy.yml` with `dorny/paths-filter@v3` detection.
- **Why:** Reduce unnecessary ACR builds and ACA rollouts; keep infra changes isolated from application pushes.
- **Triggers:** `build-deploy.yml` on `src/**`, `docker/**`, `pyproject.toml`, workflow; `deploy-infra.yml` on `infra/**` or manual.

### Kane — HITL Feedback Loop (Issues #79, #80, PR #84)
- **Date:** 2026-05-09
- **Decision 1:** Issue #79 already complete on master — `_send_hitl_email_notification()` exists and is called. Close #79 as resolved.
- **Decision 2:** Inventory processor must be a closure inside `run_hitl_decision_consumer`, capturing `orchestrator` from enclosing scope.
- **Decision 3:** Failure handling in `HITLCallbackHandler.handle_decision()` already correct — failed BC posting leaves albaran open for re-review.
- **Decision 4:** Remove `PostingResult` import (only used for removed stub).

### Ripley — Orchestrator End-to-End Diagnostics (P0, 2026-05-09)
- **Date:** 2026-05-09
- **Root Cause 1:** Upload-web missing `azure-servicebus` in Docker image (rev 0000014 logs show RuntimeError). Fix: added to `docker/upload-web/requirements.txt` (commit `5249bd1`). Action: rebuild and redeploy.
- **Root Cause 2:** Orchestrator running placeholder Go quickstart image instead of real Python code. Fixes: (1) minReplicas=1, (2) granted AcrPull role to orchestrator identity, (3) configured ACR registry with system identity, (4) deployed correct image `acrvdsdev4vtapr.azurecr.io/verdecora-orchestrator:400a159da6554dea8e9e5d189a2ff11bc4128e9f` (rev 0000014 now running, real code ✅).
- **Root Cause 3:** Upload-web also has quickstart issue (rev 0000015 ActivationFailed, 13,532 probe failures). Action: redeploy with correct image + ACR registry.
- **Immediate actions:** (1) Rebuild upload-web, (2) configure ACR, (3) re-test full flow.
- **CI/CD safeguards:** Always specify `--image` in `az containerapp update`; configure `--registry-server` before deploy; pin Docker base images in IaC.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
