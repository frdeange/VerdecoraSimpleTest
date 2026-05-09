# Burke — Project History

## Learnings

### 2026-05-09 — PO Reassignment + FANSA E2E Test Data

**Context:** Two BC tasks requested by Kiko de Angel. PO 106031 reassigned from Fabrikam to V-HERSTERA; new FANSA PO 106032 with deliberate discrepancies for E2E testing.

**Task 1 — PO Vendor Reassignment:**
- `Modify_PurchaseOrder_PAG30066` accepts `vendorId` + `vendorNumber` and BC resolves the full vendor card (address, payment terms, etc.) automatically
- BC allows vendor change on a PO that already has lines — no error, all 59 lines preserved
- `shortcutDimension1Code` was cleared automatically when changing vendor (was "PURCHASING" under Fabrikam, blank under V-HERSTERA) — expected behavior, not a problem
- OData filter `id eq '<guid>'` fails with "operand types 'Edm.Guid' and 'Edm.String'" — use `number eq '106031'` instead to retrieve POs by number

**Task 2 — FANSA Items + Discrepancy PO:**
- FANSA items didn't exist in BC → created 13 items (11 from albaran + 2 ghost items) via `Create_Item_PAG30008` with `generalProductPostingGroupCode: "RETAIL"` and `inventoryPostingGroupCode: "RESALE"`
- Parallel item creation via BC API is safe (no sequence issue — items are independent)
- PO 106032 created under V-FANSA with 11 lines including 3 quantity mismatches, 2 ghost items, and 2 albaran items deliberately omitted
- Total discrepancy triggers = 7 → should force HITL routing

**POs Summary:**
- PO 106031: GUID `bf9251d9-c64b-f111-a820-002248b5dea4`, V-HERSTERA, 59 lines, orderDate 2021-04-10 (clean match scenario)
- PO 106032: GUID `a4d08f95-e24b-f111-a820-002248b5dea4`, V-FANSA, 11 lines, orderDate 2021-04-18 (discrepancy scenario)

**Output doc:** `.squad/decisions/inbox/burke-po-reassignment.md`

---

### 2026-05-09 — Issue #83: Create test POs in Business Central

**Context:** Created E2E test data in CRONUS USA, Inc. — one 59-line Purchase Order (PO 106031) matching albaran PRUEBA-1-4.pdf exactly.

**Key blocker — Vendor Posting Group:**
- Vendors created via BC API v2.0 have no Vendor Posting Group or Gen. Bus. Posting Group set
- BC rejects PO creation with such vendors: `"Vendor Posting Group must have a value in Vendor: No.=V-HERSTERA"`
- BC API v2.0 does NOT expose these fields on any vendor endpoint — no programmatic fix
- **Fix is manual only:** open vendor card in BC UI → set Vendor Posting Group + Gen. Bus. Posting Group
- **Workaround for test data:** used Fabrikam (10000) as PO vendor — fully configured, accepts POs

**BC MCP action quirks learned:**
- `lineType` must be `"'Item'"` — single quotes embedded inside the JSON string (i.e., the enum value includes literal apostrophes)
- `lineObjectNumber` accepts the item code string directly; BC resolves to internal GUID automatically
- Line sequence numbers auto-increment by 10,000 (seq 10000, 20000, … 590000 for 59 lines)
- Parallel calls to `Create_PurchaseOrderLinesOfPurchaseOrder_PAG30067` on the same PO are risky (sequence collision) — sequential is safe
- `Create_PurchaseOrder_PAG30066` returns the PO GUID needed as `PurchaseOrder_id` for line creation

**PO created:**
- PO 106031, GUID `bf9251d9-c64b-f111-a820-002248b5dea4`, vendor 10000 (Fabrikam), orderDate 2021-04-10, 59 lines, all 59 Herstera items accepted

**Scenario 2 (FANSA) deferred:** same vendor posting group blocker applies to any new vendor created via API. Recommend manual BC UI setup before attempting.

**Output doc:** `.squad/decisions/inbox/burke-bc-test-data.md`

---

### 2026-05-09 — Issue #82: Wire BC MCP tools into agent pipeline

**Context:** PR #62 had already created `src/mcp/bc_mcp/tools.py` and wired `_build_mcp_tools()` into `OrchestratorService`, but left a critical gap that caused silent tool-name resolution failure in production.

**Root cause:** `BCToolBase.__init__()` set `self.name` and `self.description` but did NOT set `self.__name__` or `self.__doc__`. The `agent_framework.normalize_tools()` function wraps arbitrary callables as `FunctionTool` by inspecting `obj.__name__`. Without the alias, Python falls back to the bound-method name of `__call__`, yielding `"unknown_function"` for all 6 BC tools instead of `"bc.search_vendors"`, `"bc.search_purchase_orders"`, etc.

**Fix:** Two-line change to `BCToolBase.__init__()`:
```python
self.__name__ = name
self.__doc__ = description
```

**Key file paths:**
- `src/mcp/bc_mcp/tools.py` — `BCToolBase` base class; all 6 tool wrappers; `build_bc_tool_registry()`
- `src/mcp/bc_mcp/client.py` — `BCMCPClient`; 6 async methods: `list_vendors`, `list_purchase_orders`, `get_po_lines`, `search_items`, `create_purchase_receipt`, `post_purchase_receipt`
- `src/services/orchestrator/orchestration.py` — `_build_mcp_tools()` (lines ~176-199); graceful try/except fallback to zero-tool mode
- `tests/unit/mcp/test_bc_mcp.py` — regression test `test_bc_tools_normalize_with_unique_agent_framework_names`

**Architecture decisions:**
- `BCMCPClient` uses direct HTTP/OData to Business Central, not the MCP protocol — named "MCP" but REST underneath
- Tool name convention is `bc.<operation>` (e.g. `bc.search_vendors`) — dot-namespaced
- `build_bc_tool_registry()` returns `{coherence: [...], validator: [...], inventory: [...]}` keyed by agent role
- `OrchestratorService._build_mcp_tools()` wraps imports in try/except so a missing credential never hard-fails startup
- Branch `fix/bc-tool-names` (commit `8037448`) had the fix but was never merged — Issue #82 PR #85 is the proper merge path

**PR:** #85 — `squad/82-wire-bc-mcp-tools` → master

**Cross-team context:**
- Ripley's P0 root-cause analysis (2026-05-09) identified BC tool wiring as the critical blocker: agents run with zero tools. This fix unblocks the inventory posting path Kane and Ripley are building.
- Kane's HITL consumer (PR #84) depends on this fix — the inventory processor needs `orchestrator` to have live BC tool handlers to post inventory state back.
- Dallas' CI/CD (path-filtered build-deploy) will rebuild and test BC tools on any edit to `src/mcp/bc_mcp/**`.
