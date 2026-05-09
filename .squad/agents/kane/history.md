# Kane — History

## Learnings

- **2026-05-08:** Joined as Backend Dev for Verdecora Simple project. Stack is Python 3.12 + FastAPI + MAF SDK. Application uses DefaultAzureCredential for all Azure access. May need config adjustments when moving from private to public endpoints. User is Kiko de Angel.
- **2026-05-08:** Upload-web preflight Document Intelligence must receive a read-only SAS URL for private blobs; generating one user delegation key per preflight request and reusing it across files avoids repeated Azure calls and fixes private blob access.
- **2026-05-09:** Completed HITL feedback loop (PR #84). Issue #79 (send HITL email) was already complete on master; no new work needed. Issue #80 (HITL decision consumer): replaced stub with real `_inventory_processor` closure that invokes the BC MCP inventory posting on confirm/reject decisions. Failure handling is safe — if BC posting fails, albaran stays `hitl_pending` for re-review.

**Cross-team context:**
- Burke's BC tool fix (PR #85) unblocks this work — the inventory processor now has live BC tool handlers to call.
- Ripley's orchestrator P0 (root-cause analysis 2026-05-09) diagnosed that HITL consumer was stubbed out and the decision topic had no consumer; Kane fixed the consumer half; Ripley fixed the orchestrator image + upload-web dependency.
- Dallas' CI/CD (path-filtered build-deploy) will test HITL consumer on any edit to `src/services/orchestrator/**` or `src/mcp/bc_mcp/**`.
- **2026-05-09:** Fixed issue #87 E2E pipeline regressions on `squad/87-fix-e2e-pipeline`. Upload-web already synced `processing-records`, so the real bug was status normalization: `hitl_pending` was collapsed back to `processing`. Preserved `hitl_pending`/`rejected` as terminal UI states in upload-web and aligned orchestrator defaults to consume `extraccion-in`; `.env.example` now documents the two-queue topology (`extraccion-queue` → `extraccion-in`).
- **2026-05-10:** Fixed issue #98 extractor refusal in the deployed pipeline. Root cause: `AlbaranPipeline.run()` sent the raw Document Intelligence dict (`ocr_payload`) to the extractor instead of readable OCR text. Pipeline now formats OCR content/key-value pairs/tables into human-readable text, orchestrator populates `PipelineDocumentInput.raw_text` with that text, and extractor refusal / non-JSON responses are logged and routed to HITL instead of crashing. Targeted pipeline/orchestrator/security/E2E tests passed; full `tests/unit/` is still blocked by pre-existing `SequentialBuilder` import errors in learning/reconciliation.
