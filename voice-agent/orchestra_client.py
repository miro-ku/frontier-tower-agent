"""
Orchestra MCP HTTP Client

Wraps Orchestra's MCP JSON-RPC endpoint for use by the voice agent.
"""

import json
import os
from typing import Any

import httpx


class OrchestraClient:
    """HTTP client for Orchestra's MCP server."""

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        space_uid: str | None = None,
        user_uid: str | None = None,
    ):
        self.endpoint = endpoint or os.environ["ORCHESTRA_MCP_ENDPOINT"]
        self.api_key = api_key or os.environ["ORCHESTRA_API_KEY"]
        self.space_uid = space_uid or os.environ["ORCHESTRA_SPACE_UID"]
        self.user_uid = user_uid or os.environ.get("ORCHESTRA_USER_UID", "")
        self._request_id = 0

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Call an MCP tool on the Orchestra server."""
        self._request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params,
            },
            "id": f"req-{self._request_id}",
            "_context": {
                "spaceUid": self.space_uid,
                "userUid": self.user_uid,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "x-space-uid": self.space_uid,
                },
            )
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            raise Exception(f"MCP error: {result['error']}")

        # Extract text content from MCP result
        content = result.get("result", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                try:
                    return json.loads(item["text"])
                except json.JSONDecodeError:
                    return item["text"]

        return content

    # Convenience methods

    async def send_message(self, chat_uid: str, content: str, **kwargs: Any) -> Any:
        return await self.call_tool("send_message", {"chatUid": chat_uid, "content": content, **kwargs})

    async def read_messages(self, chat_uid: str, limit: int = 20) -> Any:
        return await self.call_tool("read_messages", {"chatUid": chat_uid, "limit": limit})

    async def search_entities(self, query: str, types: list[str] | None = None) -> Any:
        params: dict[str, Any] = {"query": query}
        if types:
            params["types"] = types
        return await self.call_tool("search_entities", params)

    async def get_members(self, **kwargs: Any) -> Any:
        return await self.call_tool("get_members", kwargs)

    async def get_entity(self, entity_uid: str, **kwargs: Any) -> Any:
        return await self.call_tool("get_entity", {"entityUid": entity_uid, **kwargs})

    async def create_entity(self, entities: list[dict[str, Any]]) -> Any:
        return await self.call_tool("create_entity", {"entities": entities})

    async def create_poll(self, chat_uid: str, question: str, options: list[str], **kwargs: Any) -> Any:
        return await self.call_tool("create_poll", {"chatUid": chat_uid, "question": question, "options": options, **kwargs})

    async def get_poll_results(self, message_uid: str, chat_uid: str) -> Any:
        return await self.call_tool("get_poll_results", {"messageUid": message_uid, "chatUid": chat_uid})

    async def list_fields(self, context_uid: str, target_type: str = "task") -> Any:
        return await self.call_tool("list_fields", {"contextUid": context_uid, "targetType": target_type})

    async def set_fields(self, entity_uid: str, fields: list[dict[str, Any]]) -> Any:
        return await self.call_tool("set_fields", {"entityUid": entity_uid, "fields": fields})

    async def get_current_context(self) -> Any:
        return await self.call_tool("get_current_context", {})
