# Dallas — Smart path-filtered CI/CD split

- **Date:** 2026-05-08
- **Context:** The simplified repo inherited a monolithic `build-deploy.yml` that rebuilt every image and redeployed infrastructure on every push to `master`, despite GitHub-hosted runners and Azure OIDC already being in place.
- **Decision:** Split infrastructure into a dedicated `deploy-infra.yml` workflow and redesign `build-deploy.yml` around a `detect-changes` job powered by `dorny/paths-filter@v3`, with one conditional build job and one conditional deploy job per service.
- **Why:** Reduce unnecessary ACR builds and ACA rollouts, keep infra changes isolated from application pushes, and preserve manual full-fleet deployment through `workflow_dispatch`.
- **Implementation:** `build-deploy.yml` now triggers only on workflow, `src/**`, `docker/**`, and `pyproject.toml` changes; `deploy-infra.yml` triggers only on `infra/**` or manual dispatch; both workflows run on `ubuntu-latest` and authenticate to Azure with repository OIDC variables.
