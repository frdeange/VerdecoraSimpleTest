# Parker Decision — Fix Bicep image defaults

**Date:** 2026-05-09T23:31:48Z  
**Author:** Parker (IaC Expert)  
**Issue:** #89

## Summary
Container App Bicep modules must default to the ACR `:latest` workload images instead of the public quickstart image so infra redeploys do not overwrite CI/CD-managed runtime images.

## Decisions
1. Replace every empty-image fallback in `infra/modules/container-apps.bicep` with the corresponding `${acrLoginServer}/<image>:latest` reference.
2. Replace the empty-image fallback in `infra/modules/upload-web-app.bicep` with `${acrLoginServer}/verdecora-upload-web:latest`.
3. Use `acrvdsdev4vtapr.azurecr.io` as a safety fallback only when `acrLoginServer` is empty.
4. Keep the ACA `registries` entries enabled with `identity: 'system'` whenever an ACR login server is available so both apps and jobs can pull the default ACR images.

## Rationale
The previous `quickstart:latest` fallback made every infra deployment reset Container Apps and ACA Jobs to the placeholder image whenever image override parameters were blank. CI/CD already publishes `:latest` alongside commit-SHA tags, so the IaC default should align with the real ACR repository and preserve service availability between app deployments.

## Validation
- `az bicep build --file infra/modules/main.bicep`
