"""
Unbrowse MCP Client

Connects to the Unbrowse MCP server via stdio subprocess.
Discovers available abilities and executes them as tools.
"""

import asyncio
import json
import os
from typing import Any


class UnbrowseClient:
    """Client for the Unbrowse MCP server (stdio transport)."""

    def __init__(self):
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._responses: dict[str, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None

    async def start(self) -> bool:
        """Start the Unbrowse MCP server subprocess."""
        try:
            env = {**os.environ}
            self._process = await asyncio.create_subprocess_exec(
                "npx", "-y", "getfoundry-unbrowse-mcp",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            self._reader_task = asyncio.create_task(self._read_responses())

            # Initialize the MCP connection
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "frontier-tower-agent", "version": "1.0.0"},
            })

            # Send initialized notification
            await self._send_notification("notifications/initialized", {})

            print("[unbrowse] MCP server started")
            return True
        except Exception as e:
            print(f"[unbrowse] Failed to start MCP server: {e}")
            return False

    async def stop(self):
        """Stop the Unbrowse MCP server subprocess."""
        if self._reader_task:
            self._reader_task.cancel()
        if self._process:
            self._process.terminate()
            await self._process.wait()

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available Unbrowse tools."""
        if not self._process:
            return []

        try:
            result = await self._send_request("tools/list", {})
            tools = result.get("tools", [])
            return [
                {
                    "name": f"unbrowse_{t['name']}",
                    "description": f"[Unbrowse] {t.get('description', '')}",
                    "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]
        except Exception as e:
            print(f"[unbrowse] Failed to list tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call an Unbrowse tool (strip unbrowse_ prefix)."""
        if not self._process:
            return "Unbrowse not available"

        # Strip the unbrowse_ prefix we added
        tool_name = name.removeprefix("unbrowse_")

        try:
            result = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })
            content = result.get("content", [])
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts) if texts else json.dumps(result)
        except Exception as e:
            return f"Unbrowse error: {e}"

    async def _send_request(self, method: str, params: dict) -> dict:
        """Send a JSON-RPC request and wait for response."""
        self._request_id += 1
        req_id = str(self._request_id)

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._responses[req_id] = future

        assert self._process and self._process.stdin
        self._process.stdin.write(json.dumps(message).encode() + b"\n")
        await self._process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._responses.pop(req_id, None)
            raise TimeoutError(f"Unbrowse request {method} timed out")

    async def _send_notification(self, method: str, params: dict):
        """Send a JSON-RPC notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        assert self._process and self._process.stdin
        self._process.stdin.write(json.dumps(message).encode() + b"\n")
        await self._process.stdin.drain()

    async def _read_responses(self):
        """Read JSON-RPC responses from the subprocess stdout."""
        assert self._process and self._process.stdout
        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode().strip())
                    req_id = str(msg.get("id", ""))
                    if req_id in self._responses:
                        future = self._responses.pop(req_id)
                        if "error" in msg:
                            future.set_exception(Exception(json.dumps(msg["error"])))
                        else:
                            future.set_result(msg.get("result", {}))
                except json.JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
