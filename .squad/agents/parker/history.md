# Parker — History

## Learnings

- **2026-05-08:** Joined as IaC Expert for Verdecora Simple project. Main task: strip private networking from Bicep modules while preserving all functional Azure resources. Current infra has ~27 Bicep modules. About 5-6 modules need removal and main.bicep needs significant refactoring. User is Kiko de Angel.
- **2026-05-08:** Issue #1 removed private-network composition from `infra/modules/main.bicep` and deleted the dedicated network/private-endpoint/NAT/runner/Front Door modules. `identity.bicep` has no runner-specific principal inputs, so no safe cleanup was needed there; subnet parameters remain only inside child modules until Issue #3 removes them.
- **2026-05-08:** To keep `main.bicep` buildable after removing subnet arguments, `container-apps.bicep` and `upload-web-app.bicep` now treat `infrastructureSubnetId` as optional and only emit `vnetConfiguration` when a subnet id is supplied. This preserves Issue #1 validation without changing the surviving module behavior when a subnet is still passed.
