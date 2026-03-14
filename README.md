# Frontier Tower Agent

An AI building superintendent for [Frontier Tower](https://www.frontiertower.com/), a 16-floor innovation hub in San Francisco. Built on [Orchestra](https://orch.so) — a coordination and communication platform.

The agent helps 700+ residents coordinate: onboarding, resource matching, community polls, governance, event coordination, and daily activity digests. Residents interact via **voice calls** (ElevenLabs TTS) and **text** (@mentions, DMs).

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Resident                           │
│            (voice or text)                          │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
     Voice Call              Text Message
           │                      │
           ▼                      ▼
┌──────────────────┐    ┌─────────────────────┐
│  Voice Agent     │    │  Orchestra Agent     │
│  (LiveKit Room)  │    │  (Cloud Functions)   │
│                  │    │                      │
│  Deepgram STT    │    │  Memory + Context    │
│  Claude LLM  ◄───┼────┤  40+ MCP Tools      │
│  ElevenLabs TTS  │    │  Scheduled Triggers  │
└──────────────────┘    └─────────────────────┘
           │                      │
           └──────────┬───────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  Orchestra       │
            │  Workspace       │
            │                  │
            │  16 Floor Projects│
            │  Channels        │
            │  Tasks & Polls   │
            │  Member Profiles │
            └──────────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │  Solana          │
            │  (Metaplex)      │
            │                  │
            │  On-chain ID     │
            │  PDA Wallet      │
            └──────────────────┘
```

## Prize Tracks

| Track | Integration |
|-------|-------------|
| **Frontier Tower Agent** | Core conversational agent for building coordination |
| **ElevenLabs** | Voice TTS for natural spoken interaction |
| **Unbrowse** | External data retrieval (events, local services) |
| **Metaplex Agent Registry** | On-chain agent identity on Solana |
| **human.tech** | Human coordination, governance, and community building |

## Project Structure

```
frontier-tower-agent/
├── voice-agent/               # LiveKit voice agent worker
│   ├── main.py                # Agent entry point (STT + LLM + TTS)
│   ├── orchestra_client.py    # Orchestra MCP HTTP client
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Environment variables template
├── solana/                    # Metaplex agent registration
│   ├── register-agent.ts      # Registration script
│   ├── agent-registration.json# On-chain metadata (ERC-8004)
│   └── package.json
├── prompts/                   # Agent personality & instructions
│   ├── text-prompt.md         # Full instructions (for Orchestra agent)
│   └── voice-prompt.md        # Condensed voice variant
└── docs/
    ├── architecture.md        # Detailed system architecture
    └── demo-script.md         # Demo scenarios
```

## Quick Start

### Voice Agent

```bash
cd voice-agent
pip install -r requirements.txt
cp .env.example .env.local
# Edit .env.local with your credentials
python main.py dev
```

### Metaplex Registration

```bash
cd solana
npm install
# Upload agent-registration.json to Arweave/IPFS first
AGENT_REGISTRATION_URI=https://arweave.net/... npm run register
```

## How It Works

### Text Interface (Orchestra)
1. Deploy the agent in an Orchestra workspace using instructions from `prompts/text-prompt.md`
2. Configure triggers: @mention, message_in_chat, schedule
3. Residents interact by mentioning the agent or DMing it
4. Agent uses 40+ MCP tools to manage the workspace

### Voice Interface (LiveKit + ElevenLabs)
1. Voice agent worker joins LiveKit rooms as the agent's participant
2. **Deepgram** transcribes resident speech to text
3. **Claude** processes the request with Orchestra MCP tools as function calls
4. **ElevenLabs** synthesizes the response into natural speech
5. Audio streams back to the resident in real-time

### On-chain Identity (Metaplex)
1. Agent is registered on Solana via Metaplex Agent Registry
2. Gets an MPL Core asset with AgentIdentity plugin
3. PDA wallet for potential payment capabilities
4. MCP endpoint listed in on-chain metadata for discoverability

## Key Features

- **Polls** — Create votes with `create_poll`, residents click to vote in the UI, agent reads results
- **Resource Matching** — Search member profiles by skills/interests across all 16 floors
- **Onboarding** — Welcome new residents, add to channels, create checklists
- **Daily Digest** — Scheduled activity summary across the building
- **Governance** — Run building-wide votes, track proposals
- **Voice** — Natural conversation via ElevenLabs with custom superintendent voice

## Built With

- [Orchestra](https://orch.so) — Coordination platform (workspace, tasks, messages, agents)
- [LiveKit Agents SDK](https://docs.livekit.io/agents/) — Real-time voice pipeline
- [ElevenLabs](https://elevenlabs.io) — Text-to-speech
- [Deepgram](https://deepgram.com) — Speech-to-text
- [Claude](https://anthropic.com) — LLM with function calling
- [Metaplex](https://metaplex.com) — On-chain agent identity on Solana
