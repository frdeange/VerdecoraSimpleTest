# Dallas — History

## Learnings

- **2026-05-08:** Joined as DevOps for Verdecora Simple project. Key shift: moving from self-hosted ACA runners (inside private VNet) to standard GitHub-hosted runners. Need to redesign all CI/CD workflows. User is Kiko de Angel.
- **2026-05-08:** Issue #4 redesign standardised CI/CD on GitHub-hosted Ubuntu runners and Azure OIDC (`azure/login@v2` with repo variables). `build-deploy.yml` is now a four-stage pipeline: validate → deploy-infra → build-and-push → deploy-apps. Squad automation workflows were reviewed and already compliant with `ubuntu-latest`.
