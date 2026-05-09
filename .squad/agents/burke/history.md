# Burke — Project History

## Learnings

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
