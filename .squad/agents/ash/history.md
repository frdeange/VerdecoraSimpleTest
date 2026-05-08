# Ash — History

## Learnings

- **2026-05-08:** Joined as Frontend Dev for Verdecora Simple project. Two web UIs to manage: upload-web (document upload interface) and HITL webform (human review interface). Front Door removal will affect how these are exposed. User is Kiko de Angel.
- **2026-05-08:** Updated upload-web auth redirect handling to support direct ACA public hosts via `UPLOAD_WEB_PUBLIC_ORIGIN`. Login/logout flows now stay relative by default for backward compatibility, but can emit absolute Easy Auth redirect targets when a public host must be explicit. HITL callback fallback now reads `HITL_WEBFORM_BASE_URL`, and Blob CORS/auth deployment docs were updated to point at ACA FQDNs instead of Front Door.
