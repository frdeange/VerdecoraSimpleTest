# Ripley — History

## Learnings

- **2026-05-08:** Joined as Lead for Verdecora Simple project. Goal: simplify enterprise-grade private networking infrastructure to public endpoints. User is Kiko de Angel. Original complex repo at frdeange/verdecoraTest for reference. Working in frdeange/VerdecoraSimpleTest. Target RG: rg-verdecora-simple in Sweden Central.
- **2026-05-08:** Completed the simplification analysis. Main finding: the application architecture is already fit for purpose, but the hosting model is overbuilt around private networking, Front Door, and self-hosted ACA runners. The safest simplification path is public endpoints + managed identity/RBAC + GitHub OIDC, with upload-web kept on direct ACA ingress and Blob SAS uploads retained.
