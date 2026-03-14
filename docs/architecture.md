# System Architecture

## Overview

The Frontier Tower Agent is a multi-interface AI concierge built on Orchestra's coordination platform. It operates through two parallel interfaces — text and voice — sharing the same workspace data and tool capabilities.

## Components

### 1. Orchestra Platform (Backend)

Orchestra provides the data layer, agent execution, and MCP tools:

- **Workspace** — The Frontier Tower workspace with 16 floor projects, channels, and member profiles
- **AI Agent Engine** — Executes the text-based agent (triggers, sessions, memory, tool loops)
- **MCP Server** — HTTP JSON-RPC endpoint exposing 40+ tools for external access
- **Firestore** — Real-time database for all workspace data
- **LiveKit Integration** — Video/audio call infrastructure

### 2. Voice Agent Worker (This Repo)

A standalone Python service using LiveKit Agents SDK:

```
Resident Audio → Deepgram STT → Claude LLM → ElevenLabs TTS → Audio Response
                                     ↕
                          Orchestra MCP Tools (HTTP)
```

- **STT**: Deepgram Nova-3 for accurate speech recognition
- **LLM**: Claude (Anthropic) with function-calling tools that proxy to Orchestra
- **TTS**: ElevenLabs Turbo v2.5 for low-latency natural speech
- **VAD**: Silero for voice activity detection

The voice agent runs as a persistent service that joins LiveKit rooms as a bot participant.

### 3. Solana On-chain Identity

The agent is registered on Solana via Metaplex Agent Registry:

- **MPL Core Asset** — The agent's on-chain representation
- **AgentIdentity Plugin** — Lifecycle hooks for transfer, update, execute
- **PDA Wallet** — Agent-controlled wallet for potential payments
- **Registration Document** — Off-chain metadata (ERC-8004 standard) with MCP endpoint

## Data Flow

### Text Interaction
```
1. Resident @mentions agent in Orchestra chat
2. Message trigger fires on Cloud Functions
3. Agent execution pipeline: load session → build context → LLM loop
4. LLM calls Orchestra tools (create tasks, search members, send messages)
5. Agent response streamed to the chat
```

### Voice Interaction
```
1. Resident joins LiveKit room where voice agent is present
2. Resident speaks → audio captured by LiveKit
3. Deepgram STT transcribes speech to text
4. Text sent to Claude LLM with system prompt + function tools
5. LLM decides which tools to call (e.g., search_members, create_poll)
6. Voice agent calls Orchestra MCP endpoint via HTTP
7. LLM generates response text
8. ElevenLabs TTS synthesizes response to audio
9. Audio published to LiveKit room → resident hears response
```

### Polling Flow
```
1. Agent calls create_poll → message with custom.poll data created
2. Poll rendered in Orchestra UI (MessagePoll.vue component)
3. Residents click options → votePoll() updates Firestore
4. Agent calls get_poll_results → reads vote counts
5. Agent announces results in channel
```

## Authentication

### MCP Access
- Voice agent authenticates via `x-api-key` header
- API key validated against workspace's apiKeys collection (SHA-256 hash)
- All operations scoped to the agent's workspace and permissions

### LiveKit Access
- Voice agent joins rooms with a LiveKit access token
- Token generated with agent's member UID as participant identity
- Grants: room join, publish audio, subscribe to tracks

## Workspace Structure

```
Frontier Tower (Space)
├── Floor 1-16 (Projects)
│   └── Tasks: maintenance, events, governance proposals
├── Building Announcements (Channel)
├── Events (Channel)
├── Governance (Channel)
└── Frontier Tower Agent (Blueprint PROJECT)
    ├── Description: agent instructions
    ├── Settings: triggers, model, tools
    └── Sessions: conversation history per interaction
```
