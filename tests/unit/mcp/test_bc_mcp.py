from __future__ import annotations

from types import SimpleNamespace

from agent_framework import FunctionTool, normalize_tools
from mcp.types import CallToolResult, TextContent

from src.mcp.bc_mcp.client import BCMCPClient
from src.mcp.bc_mcp.config import BCMCPSettings
from src.mcp.bc_mcp.tools import build_bc_tool_registry


class _FakeCredential:
    def get_token(self, scope: str) -> SimpleNamespace:
        return SimpleNamespace(token=f"token-for:{scope}")


def test_bc_mcp_settings_defaults_match_project_configuration() -> None:
    settings = BCMCPSettings()

    assert settings.server_url == "https://mcp.businesscentral.dynamics.com"
    assert settings.tenant_id == "562029ef-9022-45a6-b255-40cd71ebb2ce"
    assert settings.environment_name == "Production"
    assert settings.company == "CRONUS USA, Inc."
    assert settings.configuration_name == "DefaultMCPKiko"


def test_prepare_arguments_merges_context_with_operation_payload() -> None:
    client = BCMCPClient(settings=BCMCPSettings(), credential=_FakeCredential())

    prepared = client._prepare_arguments({"top": 5})

    assert prepared["tenantId"] == "562029ef-9022-45a6-b255-40cd71ebb2ce"
    assert prepared["company"] == "CRONUS USA, Inc."
    assert prepared["top"] == 5


def test_parse_tool_result_prefers_structured_content() -> None:
    result = CallToolResult(content=[TextContent(type="text", text="ignored")], structuredContent={"value": []})

    assert BCMCPClient._parse_tool_result(result) == {"value": []}


def test_build_headers_uses_default_credential_scope() -> None:
    client = BCMCPClient(settings=BCMCPSettings(), credential=_FakeCredential())

    headers = client._build_headers()

    assert headers["Authorization"] == "Bearer token-for:https://mcp.businesscentral.dynamics.com/.default"
    assert headers["x-bc-configuration-name"] == "DefaultMCPKiko"


def test_bc_tools_normalize_with_unique_agent_framework_names() -> None:
    """Each BC tool must resolve to its own namespaced name via agent_framework.normalize_tools().

    Without ``self.__name__ = name`` on BCToolBase, normalize_tools wraps every tool as a
    FunctionTool named ``unknown_function`` because it falls back to ``obj.__name__``.
    """
    registry = build_bc_tool_registry(client=SimpleNamespace())
    expected_names = {
        "coherence": ["bc.search_vendors", "bc.search_purchase_orders", "bc.search_items"],
        "validator": ["bc.search_purchase_orders", "bc.get_purchase_order_lines", "bc.search_items"],
        "inventory": ["bc.create_purchase_receipt", "bc.post_purchase_receipt"],
    }

    for agent_name, tools in expected_names.items():
        normalized = normalize_tools(registry[agent_name])
        normalized_names = [tool.name for tool in normalized if isinstance(tool, FunctionTool)]

        assert normalized_names == tools
        assert len(normalized_names) == len(set(normalized_names))
        assert "unknown_function" not in normalized_names
