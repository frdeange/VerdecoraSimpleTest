# Parker deployment notes

- Deployment issue #6 exposed name collisions with legacy `verdecoratest` resources still present in the same subscription. Simplified infra should keep deterministic `verdecora-simple`-scoped names with a short unique suffix to avoid cross-project clashes while staying stable across redeploys.
- Infrastructure-only rollouts should not try to deploy ACA workloads before container images exist in ACR. `enableContainerAppWorkloads` now defaults to `false`; enable it later when Dallas/app deployment is ready.
- AI Foundry account/project deployment can proceed without model deployments in this subscription. `enableModelDeployments` now defaults to `false` because `gpt-5` policy validation blocked the initial rollout. Model deployments should be enabled only after subscription policy/quota is confirmed.
