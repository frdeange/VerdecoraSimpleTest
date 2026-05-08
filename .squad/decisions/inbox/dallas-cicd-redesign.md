# Dallas — CI/CD Redesign Decision

- **Date:** 2026-05-08
- **Issue:** #4 — Redesign CI/CD for GitHub-hosted runners + Azure OIDC federation

## Decision

Adopt GitHub-hosted `ubuntu-latest` runners for repository CI/CD workflows and authenticate Azure deployments with GitHub OIDC federation via `azure/login@v2`.

## Why

- Removes dependency on the deprecated self-hosted runner setup.
- Aligns deployments with GitHub-native OIDC instead of runner-managed identity.
- Makes the delivery pipeline easier to reason about by splitting it into validate, infra deploy, image build, and app deploy stages.

## Consequences

- Repository variables must be configured for `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `ACR_NAME`, and `ENVIRONMENT`.
- `build-deploy.yml` now expects Azure OIDC federation to be configured before deployments can succeed.
- Squad workflows remain unchanged because they already run on GitHub-hosted runners.
