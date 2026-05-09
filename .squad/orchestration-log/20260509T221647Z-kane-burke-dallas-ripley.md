# Orchestration Log — 2026-05-09T22:16:47Z

## Session Context
- **Recovery:** Session recovered from crash
- **Milestone:** E2E test passed ✅ (PRUEBA-1-4.pdf → preflight 100% Herstera → confirm → orchestrator processed → hitl_pending)
- **Status:** Pipeline working; queue topology and UI improvements remain

## Spawned Agents

### Burke — BC MCP Adapter & PO Test Data
- **Task:** Create BC MCP tool adapter + test POs
- **Deliverables:**
  - PR #85: BCToolBase `__name__` / `__doc__` fix for MAF normalize_tools() compatibility
  - PO 106031 (Herstera, 59 lines) + PO 106032 (FANSA, 11 lines with 7 discrepancies)
  - Vendors: V-HERSTERA, V-FANSA
  - Regression test: `test_bc_tools_normalize_with_unique_agent_framework_names`
- **Status:** Complete ✅ PR merged by Ripley

### Kane — HITL Feedback Loop & Message Flow Diagnosis
- **Tasks:** Fix HITL callback handler + diagnose upload-web → orchestrator message flow
- **Key Finding:** Queue topology collapsed (extraccion-queue misused for both ingress and processing)
  - Upload-web confirm → extraccion-queue → orchestrator consumed directly (dedup bypassed)
  - Intended: extraccion-queue (ingress) → dedup → extraccion-in (processing) → orchestrator
  - Fix: Dedup target `FLOW0_TARGET_QUEUE_NAME=extraccion-in`; orchestrator `EXTRACTION_QUEUE_NAME=extraccion-in`
- **Deliverables:**
  - PR #84: HITL callback handler corrections
  - Diagnostic report: Queue topology, message flow validation, immediate + IaC cleanup recommendations
- **Status:** Complete ✅ (flow works, queue wiring documented for Issue #87)

### Dallas — CI/CD Enforcement & Manual Deploy Violation
- **Initial Violation:** Manual docker build + ACR push + ACA update (bypassed CI/CD pipeline)
- **Directive Issued:** DevOps policy — Issue → Branch → PR → Review → Merge → Auto-deploy. No manual container ops.
- **Corrective Action:** Proper CI/CD via workflow_dispatch, all 5 services deployed successfully
- **Deliverables:** Deployed infra/app state; directive captured for future enforcement
- **Status:** Complete ✅ (E2E verified; auto-deploy policy established)

### Ripley — Code Review & E2E Test
- **Tasks:** Review & merge PRs #84, #85; execute E2E test PRUEBA-1-4.pdf
- **Diagnostics:** Identified root causes (upload-web missing azure-servicebus; orchestrator running placeholder image)
  - Fixed: upload-web requirements.txt + rebuilt image
  - Fixed: orchestrator ACR pull role + correct image deployed (rev 0000014)
- **E2E Result:** Upload PRUEBA-1-4.pdf → preflight 100% Herstera → confirm 200 OK → orchestrator processed 41s → hitl_pending routed to hitl_review ✅
- **Status:** Complete ✅ (flow validated)

## Issues Closed
- #79 (resolved on master)
- #80 (fixed in PR #84)
- #82 (fixed in PR #85)
- #83 (closed)

## Issues Created for Next Sprint
- #86: UI layout improvements
- #87: Queue topology fix (dedup ingress/processing split)
- #88: DevOps CI/CD enforcement directive

## Summary
- **E2E Flow:** ✅ Confirmed working end-to-end (upload → preflight → confirm → orchestrator → HITL routing)
- **Next:** Fix queue topology (#87), UI improvements (#86), FANSA test scenario
- **Governance:** Strict CI/CD enforcement; no manual deployments
