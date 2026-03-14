"""
Frontier Tower Voice Agent

Receives meeting_join webhooks from Orchestra's external engine,
joins LiveKit rooms, and runs the voice pipeline:
Deepgram STT → Claude LLM (with Orchestra MCP tools) → ElevenLabs TTS.

The agent receives full session context (instructions, history, memories)
from Orchestra, so it shares the same "brain" as the text agent.

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
from livekit import api as livekit_api
from livekit import rtc
from livekit.agents import AgentSession, Agent, RunContext, function_tool
from livekit.plugins import silero, anthropic, deepgram, elevenlabs

from orchestra_client import OrchestraClient

load_dotenv(".env.local")

# Voice-specific prompt additions appended to Orchestra's instructions
VOICE_RULES = """

## Voice Interaction Rules
- Keep responses concise — under 3 sentences for simple questions
- Spell out acronyms for clarity
- Use natural pauses via punctuation
- Confirm actions before executing (e.g., "I'll create that poll now, okay?")
- When listing items, limit to top 3-5 and offer to share more"""


class FrontierTowerAgent(Agent):
    """Voice agent with Orchestra MCP tools as function calls."""

    def __init__(self, orchestra: OrchestraClient, instructions: str = "") -> None:
        # Append voice-specific rules to Orchestra's instructions
        full_instructions = (instructions or "You are a helpful AI assistant.") + VOICE_RULES
        super().__init__(instructions=full_instructions)
        self._orchestra = orchestra

    @function_tool()
    async def search_members(
        self,
        context: RunContext,
        query: str | None = None,
    ) -> str:
        """Search for residents in the building by skills, interests, or floor.

        Args:
            query: Search query (e.g., "machine learning", "robotics")
        """
        members = await self._orchestra.get_members()
        if isinstance(members, list):
            if query:
                q = query.lower()
                members = [
                    m for m in members
                    if q in (m.get("name", "") + " " + (m.get("description", "") or "")).lower()
                ]
            return f"Found {len(members)} residents: " + ", ".join(
                f"{m.get('name', 'Unknown')} ({m.get('description', 'No description')[:80]})"
                for m in members[:5]
            )
        return str(members)

    @function_tool()
    async def create_poll(
        self,
        context: RunContext,
        chat_uid: str,
        question: str,
        options: list[str],
    ) -> str:
        """Create a poll for residents to vote on.

        Args:
            chat_uid: UID of the channel to create the poll in
            question: The poll question
            options: List of options to vote on (2-10 choices)
        """
        await self._orchestra.create_poll(chat_uid, question, options)
        return f"Poll created: '{question}' with {len(options)} options"

    @function_tool()
    async def get_poll_results(
        self,
        context: RunContext,
        message_uid: str,
        chat_uid: str,
    ) -> str:
        """Get the current results of a poll.

        Args:
            message_uid: UID of the poll message
            chat_uid: UID of the chat containing the poll
        """
        result = await self._orchestra.get_poll_results(message_uid, chat_uid)
        return str(result)

    @function_tool()
    async def send_announcement(
        self,
        context: RunContext,
        chat_uid: str,
        message: str,
    ) -> str:
        """Send an announcement to a building channel.

        Args:
            chat_uid: UID of the channel to post in
            message: The announcement message (supports markdown)
        """
        await self._orchestra.send_message(chat_uid, message)
        return "Announcement sent successfully"

    @function_tool()
    async def create_task(
        self,
        context: RunContext,
        name: str,
        context_uid: str | None = None,
        description: str | None = None,
        assignee_uid: str | None = None,
    ) -> str:
        """Create a task (maintenance request, event, bounty).

        Args:
            name: Task title
            context_uid: Project/floor UID to create the task in
            description: Task description
            assignee_uid: UID of the member to assign to
        """
        entity: dict[str, Any] = {"type": "task", "name": name}
        if context_uid:
            entity["contextUid"] = context_uid
        if description:
            entity["description"] = description
        if assignee_uid:
            entity["assigneeUid"] = assignee_uid

        await self._orchestra.create_entity([entity])
        return f"Task '{name}' created"

    @function_tool()
    async def search_building(
        self,
        context: RunContext,
        query: str,
        entity_type: str = "task",
    ) -> str:
        """Search for tasks, projects, or documents in the building workspace.

        Args:
            query: Search query
            entity_type: Type to search for (task, project, document, channel)
        """
        result = await self._orchestra.search_entities(query, [entity_type])
        if isinstance(result, list):
            return f"Found {len(result)} results: " + ", ".join(
                r.get("name", "Unknown") for r in result[:5]
            )
        return str(result)

    @function_tool()
    async def read_messages(
        self,
        context: RunContext,
        chat_uid: str,
        limit: int = 10,
    ) -> str:
        """Read recent messages from a chat or channel.

        Args:
            chat_uid: UID of the chat to read from
            limit: Number of messages to return (default: 10)
        """
        result = await self._orchestra.read_messages(chat_uid, limit)
        if isinstance(result, list):
            lines = []
            for msg in result:
                sender = msg.get("senderName", "Unknown")
                content = msg.get("content", "")[:100]
                lines.append(f"{sender}: {content}")
            return "\n".join(lines) if lines else "No messages found"
        return str(result)


async def handle_meeting_join(payload: dict[str, Any]) -> None:
    """Handle a meeting_join trigger by joining the LiveKit room."""
    agent_info = payload.get("agent", {})
    trigger_info = payload.get("trigger", {})
    workspace_info = payload.get("workspace", {})
    context_info = payload.get("context", {})

    room_name = trigger_info.get("room_name") or trigger_info.get("origin_chat_uid", "")
    agent_member_uid = agent_info.get("member_uid", "")
    instructions = agent_info.get("instructions", "")
    history = context_info.get("history", [])

    if not room_name:
        print("[voice] No room name in webhook payload, skipping")
        return

    print(f"[voice] Joining room: {room_name} as agent: {agent_member_uid}")

    # Create Orchestra client scoped to this agent
    orchestra = OrchestraClient(
        space_uid=workspace_info.get("uid"),
        user_uid=agent_member_uid,
    )

    # Get LiveKit token for the agent
    livekit_url = os.environ.get("LIVEKIT_URL", "")
    livekit_api_key = os.environ.get("LIVEKIT_API_KEY", "")
    livekit_api_secret = os.environ.get("LIVEKIT_API_SECRET", "")

    token = (
        livekit_api.AccessToken(livekit_api_key, livekit_api_secret)
        .with_identity(f"agent-{agent_member_uid}")
        .with_name("Frontier Tower Concierge")
        .with_grants(
            livekit_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    jwt_token = token.to_jwt()

    # Build initial chat context from Orchestra's session history
    chat_context = anthropic.llm.ChatContext()
    for msg in history:
        content = msg.get("content", "")
        if not content:
            continue
        sender_type = msg.get("senderType", "")
        is_ai = msg.get("isAiMessage", False) or sender_type == "ai"
        if is_ai:
            chat_context = chat_context.append(role="assistant", text=content)
        else:
            chat_context = chat_context.append(role="user", text=content)

    # Create the voice session
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=anthropic.LLM(model="claude-sonnet-4-20250514", temperature=0.8),
        tts=elevenlabs.TTS(
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "ODq5zmih8GrVes37Dizd"),
            model="eleven_turbo_v2_5",
        ),
        vad=silero.VAD.load(),
        chat_ctx=chat_context,
    )

    # Connect to the LiveKit room
    room = rtc.Room()
    await room.connect(livekit_url, jwt_token)

    print(f"[voice] Connected to room: {room_name}")

    # Start the voice agent
    agent = FrontierTowerAgent(orchestra=orchestra, instructions=instructions)

    await session.start(room=room, agent=agent)
    await session.generate_reply(
        instructions="Greet the resident warmly. Introduce yourself as the Frontier Tower concierge and ask how you can help today."
    )

    print(f"[voice] Agent session started in room: {room_name}")

    # Keep running until room disconnects
    disconnect_event = asyncio.Event()
    room.on("disconnected", lambda: disconnect_event.set())

    await disconnect_event.wait()
    print(f"[voice] Disconnected from room: {room_name}")


async def handle_webhook(request: web.Request) -> web.Response:
    """Handle incoming webhook from Orchestra's external engine."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if payload.get("event") != "trigger":
        return web.json_response({"error": "Unknown event"}, status=400)

    trigger_type = payload.get("trigger", {}).get("type", "unknown")

    if trigger_type != "meeting_join":
        return web.json_response({
            "error": f"Unsupported trigger type: {trigger_type}. Only meeting_join is handled."
        }, status=400)

    # Handle meeting_join asynchronously — return 200 immediately
    asyncio.create_task(handle_meeting_join(payload))

    return web.json_response({
        "success": True,
        "stepsCount": 0,
        "tokensInput": 0,
        "tokensOutput": 0,
    })


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", lambda _: web.json_response({"status": "ok"}))
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frontier Tower Voice Agent")
    parser.add_argument("--port", type=int, default=int(os.environ.get("WEBHOOK_PORT", "8765")))
    args = parser.parse_args()

    print(f"[voice] Starting Frontier Tower voice agent on port {args.port}")
    print(f"[voice] Waiting for meeting_join webhooks from Orchestra...")
    web.run_app(create_app(), port=args.port)
