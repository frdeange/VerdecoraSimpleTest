# Infrastructure as Code

Bicep templates for Azure deployment.

- **modules/** - Reusable Bicep modules for common resources
- *.bicep - Top-level deployment templates

Deploy with: `az deployment group create -t main.bicep`

## Upload web notes

- Simplified infra deployments now use deterministic `verdecora-simple`-scoped resource names with a short unique suffix so they do not collide with older `verdecoratest` resources in the same subscription.
- `infra/modules/main.bicep` keeps `enableContainerAppWorkloads=false` by default. Turn it on only after the real ACA images are published to ACR; the base infra deployment only provisions the managed environment.
- Set `enableUploadWeb=true` to deploy `verdecora-upload-web-${environment}` into its own external ACA environment.
- Pass the exact direct ACA/custom-domain origins through `uploadWebBlobCorsAllowedOrigins` so Blob CORS allows browser `PUT` uploads. For the simplified model this should be `https://<app-name>.<region>.azurecontainerapps.io` (or your custom domain).
- Set `UPLOAD_WEB_PUBLIC_ORIGIN` (or `UPLOAD_WEB_PUBLIC_BASE_URL`) in the upload-web app settings when Easy Auth should emit absolute login/logout redirect targets for the final public host.
- Create the Microsoft Entra group `verdecora-store-uploaders` manually in the Azure portal, then pass its object ID(s) through `uploadWebAllowedGroupObjectIds` when enabling Easy Auth.
- Set `enableUploadWebAuth=true` only after `verdecora-upload-web-${environment}` exists in the Container Apps environment.
- Update the Entra app registration used by upload-web so its redirect URI list includes the final public host callback: `https://<upload-web-host>/.auth/login/aad/callback`. If the app registration uses a custom Application ID URI, pass it via `uploadWebAllowedAudiences`.
- Set `enableUploadWebAppGateway=true` and configure `appGwFrontendCertificateSecretId` with a Key Vault PFX secret URI before deploying the Application Gateway HTTPS listener.
- The upload UI session metadata now lives in the Cosmos `upload-sessions` container (TTL 24h, partition key `/user_oid`).
