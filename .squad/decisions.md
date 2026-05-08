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
- Infrastructure rollouts: `enableContainerAppWorkloads` defaults to `false`; enable when container images exist in ACR.
- AI Foundry deployment: `enableModelDeployments` defaults to `false` due to policy/quota validation; enable after confirmation.

### Dallas — CI/CD Redesign (Issue #4)
- **Date:** 2026-05-08
- **Decision:** Adopt GitHub-hosted `ubuntu-latest` runners and GitHub OIDC federation for Azure deployments.
- **Why:** Removes deprecated self-hosted setup; aligns with GitHub-native OIDC.
- **Consequence:** Repository variables must include `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `ACR_NAME`, `ENVIRONMENT`.

### Ash — Upload-web public endpoint config
- Upload-web treats public host as configuration: use `UPLOAD_WEB_PUBLIC_ORIGIN`.
- HITL callback fallback: `HITL_WEBFORM_BASE_URL` for final public webform host.
- Blob CORS: Allow exact upload-web origin only (ACA hostname or custom domain).

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
