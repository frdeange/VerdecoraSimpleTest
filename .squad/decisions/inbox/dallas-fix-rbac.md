# Dallas — Fix OIDC RBAC scope for subscription deployments

- **Date:** 2026-05-08
- **Context:** `build-deploy.yml` deploys `infra/modules/main.bicep` with `targetScope = 'subscription'` and creates the resource group during `az deployment sub create`.
- **Decision:** Grant the GitHub OIDC service principal `Contributor` at subscription scope, not only at the resource group scope. Keep `AcrPush` scoped to the discovered ACR resource.
- **Why:** Subscription deployments require `Microsoft.Resources/deployments/validate/action` on the subscription before the resource group exists. Resource-group-only RBAC is insufficient.
- **Implementation:** Update `scripts/setup-github-oidc.ps1` and `scripts/README.md` so future bootstrap runs provision the correct RBAC automatically.
