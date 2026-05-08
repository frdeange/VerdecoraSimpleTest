# Dallas Bootstrap OIDC Inbox

- **Date:** 2026-05-08T16:30:00+02:00
- **Issue:** Automate GitHub OIDC bootstrap for Azure deployments

## Proposal

1. Standardise Azure OIDC bootstrap in `scripts/setup-github-oidc.ps1`.
   - Reason: the repo now depends on `azure/login@v2` and GitHub repository variables, so setup needs to be reproducible and low-friction.
2. Auto-discover the active Azure subscription and the single ACR in the target resource group instead of hardcoding environment values.
   - Reason: keeps the script reusable across environments while still protecting against ambiguous ACR selection.
3. Make the script idempotent for app registration, service principal, federated credentials, and RBAC assignments.
   - Reason: reruns should converge safely after partial failures or environment drift.

## Validation Notes

- Verified the script end-to-end for `frdeange/VerdecoraSimpleTest` and `rg-verdecora-simple-dev`.
- Confirmed GitHub variables were set: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ACR_NAME`, `RESOURCE_GROUP`, `ENVIRONMENT`.
- Confirmed Azure principal details in the current environment:
  - App registration: `github-deploy-VerdecoraSimpleTest`
  - Client ID: `a9a77855-4408-463a-8eb9-e1ed217c6a95`
  - Service principal object ID: `9791eca1-a3ea-4dcd-9b78-dc844df71ebb`
