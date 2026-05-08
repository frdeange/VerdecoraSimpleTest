# Parker decision note — delete private network modules

- **Date:** 2026-05-08T14:00:32.542+02:00
- **Issue:** #1
- **Decision:** Remove private-network-only composition from `infra/modules/main.bicep` now and make subnet wiring optional in the surviving Container Apps modules so the simplified deployment still compiles.
- **Why:** This keeps the deployment graph valid for the public-endpoint target without carrying the deleted network resources forward or leaving `main.bicep` in a broken state between Issue #1 and Issue #3.
- **Impact:** `main.bicep` no longer deploys VNet, private endpoints, NAT, self-hosted runners, or Front Door. `container-apps.bicep` and `upload-web-app.bicep` only emit `vnetConfiguration` when a subnet id is provided, and Issue #3 can now focus on deeper module cleanup instead of restoring buildability.
