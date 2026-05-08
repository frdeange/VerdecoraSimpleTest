# Parker — Public PaaS access decision

- **Date:** 2026-05-08
- **Issue:** #2
- **Decision:** Re-open public network access on the core PaaS modules (`storage`, `cosmos`, `servicebus`, `keyvault`, `docintell`, `ai-foundry`, `monitoring`) using the smallest possible Bicep changes.
- **Implementation rule:** Only change explicit network exposure settings from private/deny to public/allow.
- **Security rule kept:** Identity, RBAC, and local-auth restrictions remain the primary control plane protections.
- **Preserved hardening:** Storage keeps HTTPS-only, TLS 1.2, and no blob public access; Key Vault keeps RBAC authorization; Cosmos, Service Bus, Document Intelligence, AI Foundry, and App Insights keep identity-centric auth settings already present.
