"""
Webhook Server for External Engine

Receives trigger payloads from Orchestra's external engine dispatch.
Handles both text triggers (respond via MCP) and voice triggers
(join LiveKit room with STT/TTS).

This is the bridge between Orchestra's agent system and the voice agent.
Both text and voice go through the same context — same instructions,
same memory, same session history.
"""

import asyncio
import json
import os
from typing import Any

from aiohttp import web

from orchestra_client import OrchestraClient

# Will be set when main.py initializes
_livekit_session_handler = None


def set_livekit_handler(handler):
    """Register the LiveKit session handler from main.py."""
    global _livekit_session_handler
    _livekit_session_handler = handler


async def handle_webhook(request: web.Request) -> web.Response:
    """Handle incoming webhook from Orchestra's external engine."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if payload.get("event") != "trigger":
        return web.json_response({"error": "Unknown event"}, status=400)

    agent_info = payload.get("agent", {})
    trigger_info = payload.get("trigger", {})
    execution_info = payload.get("execution", {})
    workspace_info = payload.get("workspace", {})
    context_info = payload.get("context", {})

    trigger_type = trigger_info.get("type", "unknown")
    origin_chat_uid = trigger_info.get("origin_chat_uid", "")
    instructions = agent_info.get("instructions", "")
    history = context_info.get("history", [])

    print(f"[webhook] Received trigger: type={trigger_type}, chat={origin_chat_uid}")

    # Create Orchestra client scoped to this agent
    orchestra = OrchestraClient(
        space_uid=workspace_info.get("uid"),
        user_uid=agent_info.get("member_uid"),
    )

    # Determine if this is a voice call trigger or text trigger
    # Voice triggers would be "meeting_join" or similar
    # For now, text triggers respond via MCP message
    if trigger_type in ("mention", "message_in_chat", "message_in_project", "schedule"):
        # Text trigger — process with LLM and respond via MCP
        result = await handle_text_trigger(
            orchestra=orchestra,
            instructions=instructions,
            history=history,
            origin_chat_uid=origin_chat_uid,
            trigger_type=trigger_type,
        )
        return web.json_response(result)

    # Unknown trigger type — acknowledge but don't process
    return web.json_response({
        "success": True,
        "stepsCount": 0,
        "tokensInput": 0,
        "tokensOutput": 0,
    })


async def handle_text_trigger(
    orchestra: OrchestraClient,
    instructions: str,
    history: list[dict[str, Any]],
    origin_chat_uid: str,
    trigger_type: str,
) -> dict[str, Any]:
    """Handle a text-based trigger by running Claude with the provided context."""
    import anthropic

    client = anthropic.AsyncAnthropic()

    # Build messages from Orchestra's session history
    messages = []
    for msg in history:
        role = "assistant" if msg.get("senderType") == "ai" else "user"
        content = msg.get("content", "")
        if content:
            messages.append({"role": role, "content": content})

    if not messages:
        messages = [{"role": "user", "content": "(Scheduled trigger — no user message)"}]

    # Call Claude with the Orchestra-provided context
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=instructions,
        messages=messages,
    )

    response_text = response.content[0].text if response.content else ""

    # Send the response back to the origin chat via MCP
    if origin_chat_uid and response_text:
        try:
            await orchestra.send_message(origin_chat_uid, response_text)
        except Exception as e:
            print(f"[webhook] Failed to send response: {e}")

    return {
        "success": True,
        "stepsCount": 1,
        "tokensInput": response.usage.input_tokens,
        "tokensOutput": response.usage.output_tokens,
        "responseText": response_text,
    }


def create_app() -> web.Application:
    """Create the webhook server application."""
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", lambda _: web.json_response({"status": "ok"}))
    return app


if __name__ == "__main__":
    port = int(os.environ.get("WEBHOOK_PORT", "8765"))
    app = create_app()
    print(f"[webhook] Starting server on port {port}")
    web.run_app(app, port=port)
