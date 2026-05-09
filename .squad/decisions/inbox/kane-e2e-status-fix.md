# Kane — E2E status + queue topology fix (#87)

- **Date:** 2026-05-09
- **Requested by:** Kiko de Angel

## Decision

1. **Do not add a new orchestrator write-back into `upload-sessions`.**
   Upload-web already reads `processing-records` and syncs session state from Cosmos in `src/upload_web/services/upload_session.py`.
2. **Preserve orchestrator terminal states in upload-web.**
   The real defect was `_normalize_processing_status()` mapping `hitl_pending` back to `processing`, which kept “Mis albaranes” stuck on "Procesando".
3. **Keep the intended two-queue topology explicit in code defaults.**
   Orchestrator must default to `extraccion-in`; dedup remains `extraccion-queue` → `extraccion-in`.

## Why

- This is the smallest Python-only fix and avoids coupling orchestrator to upload-web persistence rules.
- It restores truthful user-facing state without duplicating data between Cosmos containers.
- It also closes the queue-default regression that let dedup and orchestrator compete on the same queue when env vars were missing.

## Implementation

- Upload-web now surfaces `hitl_pending` as **Pendiente revisión** and `rejected` as **Rechazado**.
- Orchestrator default `EXTRACTION_QUEUE_NAME` is now `extraccion-in`.
- `.env.example` now documents canonical queue names:
  - ingress: `extraccion-queue`
  - processing: `extraccion-in`

## Validation

- `python -m ruff check src\upload_web\models\upload.py src\upload_web\routes\upload.py src\upload_web\services\upload_session.py src\services\orchestrator\config.py tests\unit\test_upload_session.py tests\unit\test_jinja_templates.py tests\unit\services\test_orchestration.py`
- `python -m pytest tests\unit\test_upload_session.py tests\unit\test_jinja_templates.py tests\unit\services\test_orchestration.py -q`

## Notes

- Requested diagnostic file `.squad/decisions/inbox/kane-message-flow-diagnostic.md` was not present in the repo at execution time.
