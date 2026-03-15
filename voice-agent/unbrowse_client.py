"""
Unbrowse Client

Connects to the Unbrowse local HTTP API for web skill execution.
Unbrowse reverse-engineers websites into direct API calls — no browser needed.

The agent can use natural language intents to interact with any website.
Unbrowse resolves the intent to the right API call automatically.
"""

import os
from typing import Any

import httpx


UNBROWSE_BASE_URL = os.environ.get("UNBROWSE_URL", "http://localhost:6969")


class UnbrowseClient:
    """Client for Unbrowse's HTTP API."""

    def __init__(self, base_url: str = UNBROWSE_BASE_URL):
        self.base_url = base_url
        self._available = False

    async def start(self) -> bool:
        """Check if Unbrowse server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                self._available = resp.status_code == 200
                if self._available:
                    print(f"[unbrowse] Connected to {self.base_url}")
                return self._available
        except Exception:
            print(f"[unbrowse] Server not available at {self.base_url}")
            return False

    async def stop(self):
        """No cleanup needed for HTTP client."""
        pass

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions for Claude."""
        if not self._available:
            return []

        return [
            {
                "name": "unbrowse_resolve",
                "description": (
                    "Execute a web action using natural language. Unbrowse resolves "
                    "the intent to direct API calls — no browser automation needed. "
                    "Examples: 'get trending topics on Hacker News', "
                    "'search Eventbrite for tech events in San Francisco this weekend', "
                    "'get current weather in San Francisco'."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "Natural language description of what to do",
                        },
                        "url": {
                            "type": "string",
                            "description": "Target website URL (optional — Unbrowse can infer from intent)",
                        },
                    },
                    "required": ["intent"],
                },
            },
            {
                "name": "unbrowse_search",
                "description": (
                    "Search Unbrowse's skill marketplace for available web abilities. "
                    "Returns skills that have been learned from other agents."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "What capability to search for",
                        },
                    },
                    "required": ["intent"],
                },
            },
        ]

    async def resolve(self, intent: str, url: str | None = None) -> str:
        """Resolve a natural language intent to a web action and execute it."""
        if not self._available:
            return "Unbrowse not available"

        try:
            payload: dict[str, Any] = {"intent": intent}
            if url:
                payload["context"] = {"url": url}

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/intent/resolve",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            return f"Unbrowse error: {e}"

    async def search(self, intent: str) -> str:
        """Search the skill marketplace."""
        if not self._available:
            return "Unbrowse not available"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/search",
                    json={"intent": intent},
                )
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            return f"Unbrowse search error: {e}"

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        """Route a tool call to the right method."""
        if name == "unbrowse_resolve":
            return await self.resolve(args["intent"], args.get("url"))
        elif name == "unbrowse_search":
            return await self.search(args["intent"])
        return f"Unknown Unbrowse tool: {name}"
