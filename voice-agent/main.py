"""
Frontier Tower Agent — External Engine Worker

Receives triggers from Orchestra's external engine webhook.
Handles text triggers (respond via MCP) and voice triggers (LiveKit).

Key features:
- Uses Orchestra's MCP server for full 40+ tool access (no duplication)
- Streams text responses into Orchestra chat (typing indicator)
- Manages Solana wallet for building treasury operations
- Voice calls via LiveKit (Deepgram STT + Claude LLM + ElevenLabs TTS)

Usage:
    python main.py                  # Start webhook server (port 8765)
    python main.py --port 9000      # Custom port
"""

import argparse
import asyncio
import json
import os
from typing import Any

import httpx
from aiohttp import web
from dotenv import load_dotenv

from orchestra_client import OrchestraClient
import solana_tools

load_dotenv(".env.local")

VOICE_RULES = """

## Voice Interaction Rules
- Keep responses concise — under 3 sentences for simple questions
- Spell out acronyms for clarity
- Use natural pauses via punctuation
- Confirm actions before executing
- When listing items, limit to top 3-5 and offer to share more"""


# ---------------------------------------------------------------------------
# Text Trigger Handler
# ---------------------------------------------------------------------------

async def handle_text_trigger(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle a text trigger: run Claude with MCP tools, stream response."""
    agent_info = payload.get("agent", {})
    trigger_info = payload.get("trigger", {})
    context_info = payload.get("context", {})
    mcp_info = payload.get("mcp", {})

    origin_chat_uid = trigger_info.get("origin_chat_uid", "")
    instructions = agent_info.get("instructions", "")
    history = context_info.get("history", [])

    # Create Orchestra client for convenience methods
    orchestra = OrchestraClient(
        endpoint=mcp_info.get("endpoint"),
        auth_token=mcp_info.get("auth_token"),
        space_uid=mcp_info.get("space_uid"),
        user_uid=mcp_info.get("user_uid"),
    )

    # Build messages from Orchestra's session history
    messages = []
    for msg in history:
        content = msg.get("content", "")
        if not content:
            continue
        is_ai = msg.get("isAiMessage", False) or msg.get("senderType") == "ai"
        messages.append({
            "role": "assistant" if is_ai else "user",
            "content": content,
        })

    if not messages:
        messages = [{"role": "user", "content": "(Scheduled trigger — no user message)"}]

    # Create thinking message for streaming
    thinking_msg = await orchestra.send_message(
        origin_chat_uid,
        "",
    )
    message_uid = thinking_msg.get("uid", "") if isinstance(thinking_msg, dict) else ""

    # Define Solana tools for function calling
    tools = [
        {
            "name": "check_balance",
            "description": "Check the agent's Solana wallet SOL balance",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "transfer_sol",
            "description": "Transfer SOL from the agent wallet to a recipient address",
            "input_schema": {
                "type": "object",
                "properties": {
                    "to_address": {"type": "string", "description": "Recipient Solana address"},
                    "amount": {"type": "number", "description": "Amount in SOL"},
                    "memo": {"type": "string", "description": "Transaction memo"},
                },
                "required": ["to_address", "amount"],
            },
        },
        {
            "name": "get_wallet_address",
            "description": "Get the agent's Solana wallet public address",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]

    # Also define key MCP tools as Anthropic function tools
    mcp_tools = [
        {
            "name": "search_members",
            "description": "Search for workspace members by name, skills, or description",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Filter: members, bots, all"},
                },
            },
        },
        {
            "name": "create_poll",
            "description": "Create a poll in a chat for residents to vote on",
            "input_schema": {
                "type": "object",
                "properties": {
                    "chatUid": {"type": "string"},
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["chatUid", "question", "options"],
            },
        },
        {
            "name": "get_poll_results",
            "description": "Get current results of a poll",
            "input_schema": {
                "type": "object",
                "properties": {
                    "messageUid": {"type": "string"},
                    "chatUid": {"type": "string"},
                },
                "required": ["messageUid", "chatUid"],
            },
        },
        {
            "name": "search_entities",
            "description": "Search for tasks, projects, documents by name",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "types": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
            },
        },
        {
            "name": "create_entity",
            "description": "Create a task, project, or document",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "name": {"type": "string"},
                                "contextUid": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["type", "name"],
                        },
                    },
                },
                "required": ["entities"],
            },
        },
    ]

    import anthropic
    client = anthropic.AsyncAnthropic()

    all_tools = tools + mcp_tools
    response_text = ""
    total_input = 0
    total_output = 0
    steps = 0

    # Tool loop
    current_messages = messages.copy()
    while True:
        steps += 1
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=instructions,
            messages=current_messages,
            tools=all_tools,
        )
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        # Check for tool calls
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if text_blocks:
            response_text = text_blocks[-1].text

        if not tool_uses or response.stop_reason == "end_turn":
            break

        # Execute tool calls
        current_messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tool_use in tool_uses:
            result = await execute_tool(tool_use.name, tool_use.input, orchestra)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result),
            })

        current_messages.append({"role": "user", "content": tool_results})

        # Stream intermediate text if available
        if message_uid and response_text:
            try:
                await orchestra.call_tool("update_ai_message", {
                    "chatUid": origin_chat_uid,
                    "messageUid": message_uid,
                    "content": response_text,
                    "isGenerating": True,
                })
            except Exception as e:
                print(f"[text] Streaming update failed: {e}")

        if steps >= 15:
            break

    # Final update — stop generating indicator
    if message_uid and response_text:
        try:
            await orchestra.call_tool("update_ai_message", {
                "chatUid": origin_chat_uid,
                "messageUid": message_uid,
                "content": response_text,
                "isGenerating": False,
            })
        except Exception as e:
            print(f"[text] Final update failed: {e}")

    return {
        "success": True,
        "stepsCount": steps,
        "tokensInput": total_input,
        "tokensOutput": total_output,
        "responseText": response_text,
    }


async def execute_tool(name: str, args: dict[str, Any], orchestra: OrchestraClient) -> str:
    """Execute a tool call — routes to Solana tools or Orchestra MCP."""
    try:
        # Solana tools (local)
        if name == "check_balance":
            return await solana_tools.check_balance()
        elif name == "transfer_sol":
            return await solana_tools.transfer_sol(
                args["to_address"], args["amount"], args.get("memo", "")
            )
        elif name == "get_wallet_address":
            return await solana_tools.get_wallet_address()
        # MCP tools (proxied to Orchestra)
        elif name == "search_members":
            return str(await orchestra.get_members(**args))
        elif name == "create_poll":
            return str(await orchestra.create_poll(
                args["chatUid"], args["question"], args["options"]
            ))
        elif name == "get_poll_results":
            return str(await orchestra.get_poll_results(
                args["messageUid"], args["chatUid"]
            ))
        elif name == "search_entities":
            return str(await orchestra.search_entities(
                args["query"], args.get("types")
            ))
        elif name == "create_entity":
            return str(await orchestra.create_entity(args["entities"]))
        else:
            # Try calling as generic MCP tool
            return str(await orchestra.call_tool(name, args))
    except Exception as e:
        return f"Tool error: {e}"


# ---------------------------------------------------------------------------
# Voice Trigger Handler
# ---------------------------------------------------------------------------

async def handle_meeting_join(payload: dict[str, Any]) -> None:
    """Handle a meeting_join trigger by joining the LiveKit room."""
    from livekit import api as livekit_api
    from livekit import rtc
    from livekit.agents import AgentSession, Agent, RunContext, function_tool
    from livekit.plugins import silero, anthropic as anthropic_lk, deepgram, elevenlabs

    agent_info = payload.get("agent", {})
    trigger_info = payload.get("trigger", {})
    workspace_info = payload.get("workspace", {})
    context_info = payload.get("context", {})
    mcp_info = payload.get("mcp", {})

    room_name = trigger_info.get("room_name") or trigger_info.get("origin_chat_uid", "")
    agent_member_uid = agent_info.get("member_uid", "")
    instructions = agent_info.get("instructions", "")
    history = context_info.get("history", [])

    if not room_name:
        print("[voice] No room name, skipping")
        return

    print(f"[voice] Joining room: {room_name}")

    orchestra = OrchestraClient(
        endpoint=mcp_info.get("endpoint"),
        auth_token=mcp_info.get("auth_token"),
        space_uid=mcp_info.get("space_uid"),
        user_uid=mcp_info.get("user_uid"),
    )

    # Generate LiveKit token
    livekit_url = os.environ.get("LIVEKIT_URL", "")
    livekit_api_key = os.environ.get("LIVEKIT_API_KEY", "")
    livekit_api_secret = os.environ.get("LIVEKIT_API_SECRET", "")

    token = (
        livekit_api.AccessToken(livekit_api_key, livekit_api_secret)
        .with_identity(f"agent-{agent_member_uid}")
        .with_name("Frontier Tower Concierge")
        .with_grants(livekit_api.VideoGrants(
            room_join=True, room=room_name,
            can_publish=True, can_subscribe=True,
        ))
    )

    # Build chat context from history
    chat_ctx = anthropic_lk.llm.ChatContext()
    for msg in history:
        content = msg.get("content", "")
        if not content:
            continue
        is_ai = msg.get("isAiMessage", False) or msg.get("senderType") == "ai"
        chat_ctx = chat_ctx.append(
            role="assistant" if is_ai else "user",
            text=content,
        )

    # Create voice agent with tools
    class VoiceAgent(Agent):
        def __init__(self):
            super().__init__(instructions=instructions + VOICE_RULES)

        @function_tool()
        async def search_members(self, ctx: RunContext, query: str = "") -> str:
            """Search residents by skills or interests."""
            members = await orchestra.get_members()
            if isinstance(members, list) and query:
                q = query.lower()
                members = [m for m in members
                    if q in (m.get("name","") + " " + (m.get("description","") or "")).lower()]
            if isinstance(members, list):
                return ", ".join(f"{m.get('name','?')}" for m in members[:5])
            return str(members)

        @function_tool()
        async def create_poll(self, ctx: RunContext, chat_uid: str, question: str, options: list[str]) -> str:
            """Create a poll for residents to vote on."""
            await orchestra.create_poll(chat_uid, question, options)
            return f"Poll created: {question}"

        @function_tool()
        async def check_balance(self, ctx: RunContext) -> str:
            """Check building treasury balance."""
            return await solana_tools.check_balance()

        @function_tool()
        async def transfer_sol(self, ctx: RunContext, to_address: str, amount: float, memo: str = "") -> str:
            """Transfer SOL from the building treasury."""
            return await solana_tools.transfer_sol(to_address, amount, memo)

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=anthropic_lk.LLM(model="claude-sonnet-4-20250514", temperature=0.8),
        tts=elevenlabs.TTS(
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "ODq5zmih8GrVes37Dizd"),
            model="eleven_turbo_v2_5",
        ),
        vad=silero.VAD.load(),
        chat_ctx=chat_ctx,
    )

    room = rtc.Room()
    await room.connect(livekit_url, token.to_jwt())

    await session.start(room=room, agent=VoiceAgent())
    await session.generate_reply(
        instructions="Greet the resident warmly as the Frontier Tower concierge."
    )

    print(f"[voice] Session started in room: {room_name}")

    disconnect_event = asyncio.Event()
    room.on("disconnected", lambda: disconnect_event.set())
    await disconnect_event.wait()
    print(f"[voice] Disconnected from room: {room_name}")


# ---------------------------------------------------------------------------
# Webhook Server
# ---------------------------------------------------------------------------

async def handle_webhook(request: web.Request) -> web.Response:
    """Handle incoming webhook from Orchestra's external engine."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if payload.get("event") != "trigger":
        return web.json_response({"error": "Unknown event"}, status=400)

    trigger_type = payload.get("trigger", {}).get("type", "unknown")
    print(f"[webhook] Received trigger: {trigger_type}")

    if trigger_type == "meeting_join":
        asyncio.create_task(handle_meeting_join(payload))
        return web.json_response({"success": True, "stepsCount": 0, "tokensInput": 0, "tokensOutput": 0})
    elif trigger_type in ("mention", "message_in_chat", "message_in_project", "schedule", "personal_chat", "reply"):
        result = await handle_text_trigger(payload)
        return web.json_response(result)
    else:
        return web.json_response({"error": f"Unsupported trigger: {trigger_type}"}, status=400)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frontier Tower Agent — External Engine Worker")
    parser.add_argument("--port", type=int, default=int(os.environ.get("WEBHOOK_PORT", "8765")))
    args = parser.parse_args()

    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", lambda _: web.json_response({"status": "ok"}))

    print(f"[agent] Frontier Tower Agent starting on port {args.port}")
    print(f"[agent] Handles: text triggers (streaming) + voice calls (LiveKit)")
    print(f"[agent] Solana wallet: enabled" if os.environ.get("SOLANA_PRIVATE_KEY") or os.environ.get("SOLANA_KEYPAIR_PATH") else "[agent] Solana wallet: not configured")
    web.run_app(app, port=args.port)
