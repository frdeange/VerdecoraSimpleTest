# Decisions — Verdecora Simple Simplification

## Entry: Ripley simplification analysis
**Date:** 2026-05-08T13:30:11.303+02:00  
**Author:** Ripley

### Proposed decisions

1. Replace the private-network-first deployment model with a public-endpoint Azure model while preserving the current application/service architecture.
2. Use `rg-verdecora-simple` as the default target resource group for this simplified repo.
3. Delete these infrastructure modules from the working design:
   - `infra/modules/network.bicep`
   - `infra/modules/private-endpoints.bicep`
   - `infra/modules/nat-gateway.bicep`
   - `infra/modules/runners.bicep`
   - `infra/modules/frontdoor.bicep`
4. Remove the self-hosted GitHub runner pattern and move all delivery workflows to GitHub-hosted runners.
5. Use GitHub OIDC federation with Azure for deployment authentication; do not keep long-lived deployment secrets.
6. Keep upload-web on direct public ACA ingress and keep the existing browser-to-Blob SAS upload pattern.
7. Reconfigure Storage, Cosmos, Service Bus, Key Vault, Document Intelligence, AI Foundry, and monitoring modules for public endpoint access with identity-first hardening.
8. Treat the migration as phased infra/DevOps PRs rather than a big-bang rewrite.

### Key rationale

- The current repo is structurally sound at the application level; the main excess complexity is in networking and runner bootstrap.
- The original repo history shows repeated operational friction around upload-web, private storage, and runner/network coupling.
- Public endpoints plus managed identity, Entra auth, RBAC, strict CORS, and least-privilege deployment roles are sufficient for the current delivery target.

### Risks to manage

- Upload-web hostname/CORS/auth alignment after Front Door removal
- Public-access enablement on services currently set to `Disabled`/`Deny`
- CI/CD cutover from runner identity to GitHub OIDC

### Recommended sequencing

1. Establish GitHub OIDC
2. Remove runner dependency
3. Remove network/NAT/private endpoints/Front Door from IaC
4. Open required PaaS services safely
5. Simplify ACA environments
6. Validate upload-web end to end

---

## Entry: Delete Private-Network Bicep Modules
**Date:** 2026-05-08T14:00:00+02:00  
**Author:** Parker (IaC Expert)  
**Issue:** #1

### Summary
Executed deletion of 5 Bicep network modules and associated GitHub runner Dockerfile as planned in Ripley's simplification decision.

### Actions Taken
- Deleted `infra/modules/network.bicep`
- Deleted `infra/modules/private-endpoints.bicep`
- Deleted `infra/modules/nat-gateway.bicep`
- Deleted `infra/modules/runners.bicep`
- Deleted `infra/modules/frontdoor.bicep`
- Deleted `infra/Dockerfile.github-runner`
- Cleaned `infra/main.bicep` to remove module references

### Outcome
- 5 Bicep modules removed from IaC
- main.bicep updated to remove module calls
- GitHub runner Dockerfile deleted
- PR #8 created with all changes
- Network infrastructure files no longer in repo

---

## Entry: Redesign CI/CD for GitHub-Hosted Runners + OIDC
**Date:** 2026-05-08T14:00:00+02:00  
**Author:** Dallas (DevOps)  
**Issue:** #4

### Summary
Redesigned 4 CI/CD workflows to use GitHub-hosted `ubuntu-latest` runners with GitHub OIDC federation for Azure authentication. Removed all self-hosted runner dependencies.

### Actions Taken
- Updated `.github/workflows/build-deploy.yml` for ubuntu-latest + OIDC
- Updated `.github/workflows/ci.yml` for ubuntu-latest + OIDC
- Updated `.github/workflows/bicep-validate.yml` for ubuntu-latest + OIDC
- Updated `.github/workflows/upload-web-ci.yml` for ubuntu-latest + OIDC
- Configured GitHub OIDC provider federation with Azure
- Replaced long-lived secrets with short-lived token auth

### Outcome
- 4 workflows redesigned for GitHub-hosted runners
- OIDC federation established for Azure deployment authentication
- No long-lived secrets in CI/CD pipeline
- PR #9 created with all workflow changes
- Self-hosted runner infrastructure no longer needed in CI/CD
