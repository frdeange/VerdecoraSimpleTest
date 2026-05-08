# Kane — History

## Learnings

- **2026-05-08:** Joined as Backend Dev for Verdecora Simple project. Stack is Python 3.12 + FastAPI + MAF SDK. Application uses DefaultAzureCredential for all Azure access. May need config adjustments when moving from private to public endpoints. User is Kiko de Angel.
- **2026-05-08:** Upload-web preflight Document Intelligence must receive a read-only SAS URL for private blobs; generating one user delegation key per preflight request and reusing it across files avoids repeated Azure calls and fixes private blob access.
- **2026-05-09:** Confirmed upload-web sessions now need to publish to Service Bus queue `extraccion-queue` with explicit `blob_url`, `session_id`, `user_oid`, `user_name`, and timestamp so Flow0 dedup can normalize the payload and forward it into `extraccion-in` for the orchestrator.
