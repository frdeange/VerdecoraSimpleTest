# Lambert — History

## Learnings

- **2026-05-08:** Joined as Tester for Verdecora Simple project. Need to validate that all services work correctly after removing private networking. Key areas: orchestrator health checks, Service Bus connectivity, CosmosDB access, Document Intelligence OCR, upload-web functionality. User is Kiko de Angel.
- **2026-05-08 15:00:** Parker deployment complete to rg-verdecora-simple-dev. Deployment endpoints now available for integration testing:
  - **Cosmos DB:** `cosmos-vds-dev-4vtapr.documents.azure.com` (public access enabled)
  - **Service Bus:** `sb-vds-dev-4vtapr.servicebus.windows.net` (public access enabled)
  - **Storage:** `stvdsdev4vtapr.blob.core.windows.net` (public access enabled)
  - **AI Foundry:** `vds-ais-dev-4vtapr` (AI services for OCR/document processing)
  - **Key Vault:** `kv-vds-dev-4vtapr.vault.azure.net` (secrets & connection strings)
  - **ACR:** `acrvdsdev4vtapr.azurecr.io` (awaiting container images from Dallas CI/CD)
  - Ready to begin: service connectivity tests, OCR workflow validation, upload-web e2e tests
