"""Wrap BCMCPClient operations as agent-framework-compatible Tool objects for the pipeline.

Each wrapper exposes a ``name``, ``description``, and async ``__call__`` so the MAF
agent runtime can invoke it the same way it would a native ``agents.Tool``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.mcp.bc_mcp.client import BCMCPClient

logger = logging.getLogger(__name__)


class BCToolBase:
    """Base class for BC MCP tool wrappers compatible with agent_framework."""

    def __init__(self, client: BCMCPClient, *, name: str, description: str) -> None:
        self.name = name
        self.description = description
        # agent_framework treats callable objects as raw callables and wraps them with
        # its own FunctionTool helper, which derives the tool name from ``__name__``.
        # Without these aliases every BC tool is normalized as ``unknown_function``.
        self.__name__ = name
        self.__doc__ = description
        self._client = client

    async def __call__(self, **kwargs: Any) -> str:
        raise NotImplementedError


class SearchVendorsTool(BCToolBase):
    def __init__(self, client: BCMCPClient) -> None:
        super().__init__(
            client,
            name="bc.search_vendors",
            description="Search Business Central vendors by OData filter expression. Returns id, number, displayName.",
        )

    async def __call__(self, *, filter: str | None = None, top: int = 25, **_: Any) -> str:
        vendors = await self._client.list_vendors(filter=filter, top=top)
        return json.dumps([v.model_dump(mode="json") for v in vendors], ensure_ascii=False, default=str)


class SearchPurchaseOrdersTool(BCToolBase):
    def __init__(self, client: BCMCPClient) -> None:
        super().__init__(
            client,
            name="bc.search_purchase_orders",
            description="Search Business Central purchase orders by OData filter. Returns id, number, vendorName, status.",
        )

    async def __call__(self, *, filter: str | None = None, top: int = 25, **_: Any) -> str:
        orders = await self._client.list_purchase_orders(filter=filter, top=top)
        return json.dumps([o.model_dump(mode="json") for o in orders], ensure_ascii=False, default=str)


class GetPurchaseOrderLinesTool(BCToolBase):
    def __init__(self, client: BCMCPClient) -> None:
        super().__init__(
            client,
            name="bc.get_purchase_order_lines",
            description="Get line items for a specific BC purchase order. Requires purchase_order_id.",
        )

    async def __call__(self, *, purchase_order_id: str, top: int = 200, **_: Any) -> str:
        lines = await self._client.get_po_lines(purchase_order_id, top=top)
        return json.dumps([line.model_dump(mode="json") for line in lines], ensure_ascii=False, default=str)


class SearchItemsTool(BCToolBase):
    def __init__(self, client: BCMCPClient) -> None:
        super().__init__(
            client,
            name="bc.search_items",
            description="Search BC items (products) by name or number. Returns id, number, displayName, unitCost.",
        )

    async def __call__(self, *, search_text: str = "", top: int = 25, **_: Any) -> str:
        items = await self._client.search_items(search_text, top=top)
        return json.dumps([i.model_dump(mode="json") for i in items], ensure_ascii=False, default=str)


class CreatePurchaseReceiptTool(BCToolBase):
    def __init__(self, client: BCMCPClient) -> None:
        super().__init__(
            client,
            name="bc.create_purchase_receipt",
            description="Create a new purchase receipt header in Business Central.",
        )

    async def __call__(self, **payload: Any) -> str:
        result = await self._client.create_purchase_receipt(payload)
        return json.dumps(result, ensure_ascii=False, default=str) if result else "{}"


class PostPurchaseReceiptTool(BCToolBase):
    def __init__(self, client: BCMCPClient) -> None:
        super().__init__(
            client,
            name="bc.post_purchase_receipt",
            description="Post (receive & invoice) a purchase order in Business Central.",
        )

    async def __call__(self, *, purchase_order_id: str, **_: Any) -> str:
        result = await self._client.post_purchase_receipt(purchase_order_id)
        return json.dumps(result, ensure_ascii=False, default=str) if result else "{}"


def build_bc_tool_registry(client: BCMCPClient) -> dict[str, list[Any]]:
    """Build the ToolRegistry mapping agent names → their BC MCP tools.

    Returns a dict keyed by agent name (coherence, validator, inventory)
    whose values are lists of tool objects with ``name``, ``description``
    and async ``__call__``.
    """
    search_vendors = SearchVendorsTool(client)
    search_pos = SearchPurchaseOrdersTool(client)
    get_po_lines = GetPurchaseOrderLinesTool(client)
    search_items = SearchItemsTool(client)
    create_receipt = CreatePurchaseReceiptTool(client)
    post_receipt = PostPurchaseReceiptTool(client)

    return {
        "coherence": [search_vendors, search_pos, search_items],
        "validator": [search_pos, get_po_lines, search_items],
        "inventory": [create_receipt, post_receipt],
    }
