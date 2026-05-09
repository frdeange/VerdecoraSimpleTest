# Orchestrator End-to-End Diagnostics — 2026-05-09

**Author:** Ripley (Lead Architect)  
**Requested by:** Kiko de Angel  
**Priority:** P0  
**Status:** Root causes identified, partial fix applied  

---

## Executive Summary

The orchestrator pipeline was completely non-functional. Two independent root causes were blocking message flow:

1. **Upload-web never published messages to Service Bus** — the `azure-servicebus` Python package was missing from the upload-web Docker image
2. **Orchestrator was running a placeholder image** — the ACA container app was running `mcr.microsoft.com/k8se/quickstart:latest` instead of the real orchestrator code

Both issues are now understood. The orchestrator image is fixed (deployed revision 0000014 with real code). The upload-web dependency fix is committed but needs a Docker rebuild + redeploy.

---

## Root Cause 1: Missing `azure-servicebus` in Upload-Web

**Impact:** No messages ever reached `extraccion-queue`. All confirmed albaranes stayed at "Confirmado" forever.

**Evidence (upload-web revision 0000014 logs):**
```
RuntimeError: Missing optional dependency for Azure security helpers: azure.servicebus.
Install the Azure SDK packages required by this service before using these helpers.
```

**Why it was silent:** The `_publish_to_service_bus()` function is best-effort — it catches all exceptions, logs the error, and returns `False`. The `/confirm` endpoint still returns HTTP 200 and marks the session as confirmed. The user sees "En proceso / Pendiente" with no indication the message was never sent.

**Fix:** Added `azure-servicebus>=7.13.0` to `docker/upload-web/requirements.txt` (commit `5249bd1`).

**Action needed:** Rebuild and redeploy the upload-web Docker image.

---

## Root Cause 2: Orchestrator Running Placeholder Image

**Impact:** Even if messages HAD arrived in the queue, the orchestrator was a Go "Hello World" app — not our Python FastAPI agent pipeline.

**Evidence:**
- Container image was `mcr.microsoft.com/k8se/quickstart:latest`
- Console logs showed `Listening on :80...` (Go quickstart) instead of `Uvicorn running on http://0.0.0.0:8080`
- ACA system logs: `The TargetPort 8080 does not match the listening port 80`

**How it happened:** Running `az containerapp update --min-replicas 1` (or similar infrastructure commands) WITHOUT specifying `--image` creates a new revision. If no ACR registry is configured on the container app, the new revision defaults to the quickstart placeholder.

**Contributing factors:**
- `minReplicas=0` with KEDA Service Bus scaler → orchestrator scaled to zero when the queue was empty
- No ACR registry was configured on the container app (the `--registry-server` setting)
- ACA's "Single" revision mode meant the latest (broken) revision took 100% traffic

**Fix applied:**
1. Set `minReplicas=1` so the orchestrator always runs
2. Granted AcrPull role to orchestrator's system-assigned managed identity
3. Configured ACR registry with system identity authentication
4. Deployed correct image `acrvdsdev4vtapr.azurecr.io/verdecora-orchestrator:400a159da6554dea8e9e5d189a2ff11bc4128e9f`
5. Current revision: `verdecora-orchestrator-dev--0000014` (running, port 8080, real code)

---

## Root Cause 3: Upload-Web ALSO Has Quickstart Revision Issue

**Impact:** The upload-web has the same problem — revision 0000015 is `quickstart:latest` with `ActivationFailed`. Traffic is 100% on 0000015 but ACA falls back to revision 0000014 (real code) because the quickstart can't activate.

**Evidence:**
- Revision 0000014: real image, traffic=0, Running
- Revision 0000015: quickstart, traffic=100, ActivationFailed
- 13,532 startup probe failures logged

**Risk:** This is fragile. If ACA decides to deactivate revision 0000014, the upload-web goes down entirely.

**Action needed:** Redeploy upload-web with correct image + ACR registry configured (same fix as orchestrator).

---

## Infrastructure Checks (All Clear)

| Check | Result |
|-------|--------|
| Storage public access | ✅ Enabled |
| CosmosDB public access | ✅ Enabled |
| Service Bus queue exists | ✅ `extraccion-queue` present |
| Queue messages | 0 active, 0 dead letter (expected — nothing was ever published) |
| Orchestrator env vars | ✅ All present (COSMOS, SB, DI, AOAI, ACS, KV, AppInsights) |

---

## Test Upload Results

| Session | Timestamp | File | Status | SB Published? |
|---------|-----------|------|--------|---------------|
| ac58fbdd-... | 08:03 | PRUEBA-5.pdf | Confirmado | ❌ No (missing azure-servicebus) |
| 43dc6ae6-... | ~08:34 | PRUEBA-5.pdf | Confirmado | ❌ No (same dependency error) |

---

## Recommendations

### Immediate (today)
1. **Rebuild upload-web Docker image** with the fixed requirements.txt and redeploy
2. **Configure ACR registry on upload-web** container app with system identity (same as orchestrator fix)
3. **Re-test the full flow** after redeploy: upload → preflight → confirm → SB publish → orchestrator pickup → agent pipeline

### Short-term (this sprint)
4. **Add `azure-servicebus` success/failure logging** to the status page — users should know if their confirm actually queued a message
5. **CI/CD must always specify `--image`** in `az containerapp update` commands — never let it default
6. **CI/CD must configure `--registry-server`** before any image deploy
7. **Add a health check endpoint** to the orchestrator that verifies SB connectivity at startup

### Medium-term
8. **Consider moving SB publish to synchronous with retry** instead of best-effort — a failed publish should block the confirm and show the user an error
9. **Add queue depth monitoring** — alert if `extraccion-queue` has > 0 messages for more than 5 minutes
10. **Pin Docker base images** and container app images in IaC to prevent quickstart drift

---

## Timeline of Events

| Time (UTC) | Event |
|------------|-------|
| 2026-05-08 ~20:47 | Orchestrator container app created via Bicep |
| 2026-05-09 00:21 | Revision 0000009: real orchestrator image deployed |
| 2026-05-09 08:02 | Revision 0000011: quickstart placeholder took over (cause: infra update without --image) |
| 2026-05-09 08:03 | Test upload (ac58fbdd): confirmed, SB publish failed (missing dependency) |
| 2026-05-09 ~08:25 | Diagnosis started: found minReplicas=0, set to 1 |
| 2026-05-09 ~08:28 | Discovered placeholder image (Listening on :80, port mismatch) |
| 2026-05-09 ~08:30 | Configured ACR, granted AcrPull, deployed real image (rev 0000012) |
| 2026-05-09 ~08:32 | Registry config lost on new revision (rev 0000013 = quickstart again) |
| 2026-05-09 ~08:33 | Re-configured registry, deployed real image (rev 0000014) ✅ |
| 2026-05-09 ~08:34 | Second test upload (43dc6ae6): confirmed, SB publish failed (same dependency issue) |
| 2026-05-09 ~08:36 | **Root cause found**: upload-web missing azure-servicebus package |
| 2026-05-09 ~08:37 | Fix committed: added azure-servicebus to requirements.txt |
