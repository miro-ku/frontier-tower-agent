# Demo Script

Five scenarios demonstrating the Frontier Tower Agent. Total: ~5 minutes.

**Prerequisites**:
- Agent deployed on Railway with webhook URL set in Orchestra blueprint
- Demo workspace with floor projects, channels, sample residents with descriptions
- Agent blueprint configured: external engine, voice engine, mention + voice call triggers
- Solana wallet funded with devnet SOL (optional, for scenario 5)

---

## Scenario 1: Text — Resource Matching (~1.5 min)

**Where**: @mention agent in a project or channel chat

1. Type: `@Concierge I need someone who knows about machine learning for a project`
2. Wait for agent response — it will:
   - Call `get_members` via MCP to search workspace members
   - Match based on member descriptions/profiles
   - Respond with 2-3 matches and their backgrounds
3. Type: `Can you introduce me to [name]?`
4. Agent sends a DM to that person with introduction via `send_message`

**What judges see**: Agent discovers tools dynamically from MCP, searches real workspace data, sends cross-chat messages.

---

## Scenario 2: Text — Building Poll (~1 min)

**Where**: Same chat or a channel

1. Type: `@Concierge Let's vote on common area furniture. Options: modern minimalist, cozy lounge, standing desks`
2. Agent calls `create_poll` via MCP
3. **Show**: Poll appears in the chat with clickable vote buttons
4. Click to vote on an option
5. Type: `@Concierge What are the results?`
6. Agent calls `get_poll_results`, reads back the tally

**What judges see**: Custom poll UI rendered in Orchestra, atomic voting, real-time results.

---

## Scenario 3: Voice — Onboarding Call (~2 min)

**Where**: Personal chat with the agent → start a voice call

1. Call connects — agent joins via LiveKit (Deepgram STT → Claude → ElevenLabs TTS)
2. Agent greets: *"Welcome to Frontier Tower! I'm the building concierge."*
3. Say: *"I just moved to floor 7. I work on robotics and computer vision."*
4. Agent responds conversationally, asks about interests
5. Say: *"Can you add me to the events channel?"*
6. Agent uses MCP tools during the call to add member to channel
7. **Show**: Orchestra UI updates in real-time — member added

**What judges see**: Natural voice conversation with real-time workspace actions. ElevenLabs voice quality. LiveKit infrastructure.

---

## Scenario 4: Pre-built — Daily Digest (~30 sec)

**Show**: A pre-generated scheduled digest message in the announcements channel:

```
📊 Frontier Tower Daily Digest — March 15, 2026

🆕 Activity
- 8 tasks created across 4 floors
- 3 new residents joined

💬 Active Discussions
- Floor 5: Lab equipment sharing (12 messages)
- Governance: Parking proposal (6 messages)

📅 Upcoming
- Friday Mixer — Floor 1 Common Area, 6pm
```

Explain: *"This is generated on a schedule trigger — the agent reads activity across all channels and projects, summarizes it, and posts daily."*

---

## Scenario 5: On-chain Identity (~30 sec)

**Option A** (if Metaplex registration done):
1. Show Solana Explorer with the agent's MPL Core asset
2. Point out: agent name, MCP endpoint in metadata, PDA wallet
3. Say: *"The agent has a verifiable on-chain identity via Metaplex Agent Registry"*

**Option B** (if Solana wallet funded):
1. Ask agent: *"What's the building treasury balance?"*
2. Agent calls `check_balance`, returns devnet SOL amount
3. Say: *"The agent manages a Solana wallet for building governance — bounties, proposals, community funds"*

---

## Key Talking Points

- **Orchestra provides**: Agent identity, 40+ MCP tools, session management, trigger system, workspace data
- **External engine**: Agent runs anywhere (Railway), connects back to Orchestra via MCP
- **No tool duplication**: Agent discovers tools dynamically from MCP at runtime
- **Voice + Text**: Same agent, same tools, different interface — voice via LiveKit + ElevenLabs, text via streaming webhook
- **JWT-scoped auth**: Agent gets a short-lived token scoped to the workspace, no stored credentials
