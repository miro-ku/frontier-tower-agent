"""
Frontier Tower Voice Agent

LiveKit Agents SDK worker that provides a voice interface to the
Frontier Tower concierge agent. Uses Deepgram STT, Claude LLM with
Orchestra MCP tools, and ElevenLabs TTS.
"""

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, RunContext, function_tool
from livekit.plugins import silero, anthropic, deepgram, elevenlabs
from typing import Any

from orchestra_client import OrchestraClient

load_dotenv(".env.local")

# Shared Orchestra client instance
orchestra = OrchestraClient()

SYSTEM_PROMPT = """You are the Frontier Tower Building Concierge — a warm, knowledgeable AI superintendent for a 16-floor innovation hub in San Francisco, home to 700+ members across AI, robotics, neurotech, biotech, arts, and the Ethereum Foundation.

## Personality
- Friendly, professional, like a great hotel concierge
- Concise in voice responses (under 3 sentences for simple questions)
- Uses natural speech patterns — contractions, conversational tone
- Proactive about community building and connecting residents

## Building Structure
Each floor is a Project in Orchestra. Residents are workspace members with descriptions of their interests and skills.

## What You Can Do
1. **Onboard new residents** — welcome them, learn their interests, add to relevant floor channels
2. **Run polls** — create building-wide votes on decisions
3. **Match resources** — find residents with specific skills by searching member profiles
4. **Send announcements** — post to building channels
5. **Create tasks** — maintenance requests, event planning, bounties
6. **Activity digest** — summarize what's happening across the building

## Voice Interaction Rules
- Keep responses concise — under 3 sentences for simple questions
- Spell out acronyms for clarity
- Use natural pauses via punctuation
- Confirm actions before executing (e.g., "I'll create that poll now, okay?")
- When listing items, limit to top 3-5 and offer to share more"""


class FrontierTowerAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    @function_tool()
    async def search_members(
        self,
        context: RunContext,
        query: str | None = None,
        floor: str | None = None,
    ) -> str:
        """Search for residents in the building by skills, interests, or floor.

        Args:
            query: Search query (e.g., "machine learning", "robotics")
            floor: Floor number to filter by
        """
        members = await orchestra.get_members()
        if isinstance(members, list):
            # Filter by query if provided
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
        result = await orchestra.create_poll(chat_uid, question, options)
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
        result = await orchestra.get_poll_results(message_uid, chat_uid)
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
        result = await orchestra.send_message(chat_uid, message)
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

        result = await orchestra.create_entity([entity])
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
        result = await orchestra.search_entities(query, [entity_type])
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
        result = await orchestra.read_messages(chat_uid, limit)
        if isinstance(result, list):
            lines = []
            for msg in result:
                sender = msg.get("senderName", "Unknown")
                content = msg.get("content", "")[:100]
                lines.append(f"{sender}: {content}")
            return "\n".join(lines) if lines else "No messages found"
        return str(result)


server = AgentServer()


@server.rtc_session(agent_name="frontier-tower")
async def frontier_tower_session(ctx: agents.JobContext):
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="en",
        ),
        llm=anthropic.LLM(
            model="claude-sonnet-4-20250514",
            temperature=0.8,
        ),
        tts=elevenlabs.TTS(
            voice_id="ODq5zmih8GrVes37Dizd",  # Patrick - warm, professional
            model="eleven_turbo_v2_5",
        ),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=FrontierTowerAgent(),
    )

    await session.generate_reply(
        instructions="Greet the resident warmly. Introduce yourself as the Frontier Tower concierge and ask how you can help today."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
