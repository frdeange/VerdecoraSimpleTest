# Dallas — History

## Learnings

- **2026-05-08:** Joined as DevOps for Verdecora Simple project. Key shift: moving from self-hosted ACA runners (inside private VNet) to standard GitHub-hosted runners. Need to redesign all CI/CD workflows. User is Kiko de Angel.
- **2026-05-08:** Issue #4 redesign standardised CI/CD on GitHub-hosted Ubuntu runners and Azure OIDC (`azure/login@v2` with repo variables). `build-deploy.yml` is now a four-stage pipeline: validate → deploy-infra → build-and-push → deploy-apps. Squad automation workflows were reviewed and already compliant with `ubuntu-latest`.
- **2026-05-08 14:00:** Completed Issue #4 — redesigned 4 CI/CD workflows (build-deploy, ci, bicep-validate, upload-web-ci) for ubuntu-latest runners. Configured GitHub OIDC federation with Azure. Replaced long-lived secrets with short-lived token auth. PR #9 created. Successfully unblocked by Parker's Issue #1 (private-network module deletions), no self-hosted runner infrastructure dependency remains. OIDC federation now foundational for Parker's subsequent PaaS public-access configuration.
- **2026-05-08 15:00:** Parker deployment to rg-verdecora-simple-dev complete. Infrastructure ready for CI/CD. ACR: `acrvdsdev4vtapr.azurecr.io`; Cosmos: `cosmos-vds-dev-4vtapr.documents.azure.com`; KV: `kv-vds-dev-4vtapr.vault.azure.net`. Configure repository variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `RESOURCE_GROUP`, `ACR_NAME`, `ENVIRONMENT`) and trigger build-deploy workflow to push container images.
