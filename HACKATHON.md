# Hackathon Status — Intelligence at the Frontier

**Event**: Intelligence at the Frontier Hackathon, SF
**Submission deadline**: March 15, 2026
**Repo**: https://github.com/miro-ku/frontier-tower-agent

---

## Prize Tracks

| Track | Status | What We Built |
|-------|--------|---------------|
| **Frontier Tower Agent** (primary) | Code done | Conversational agent for 16-floor building coordination |
| **ElevenLabs Voice** | Code done | Voice calls via LiveKit + Deepgram STT + ElevenLabs TTS |
| **Metaplex Agent Registry** | Code done, not run | On-chain agent identity + Solana wallet |
| **Unbrowse** | Config only | Orchestra's External Tools supports Direct MCP — no code needed |
| **human.tech** | Skipped | Would need Human Passport integration |

---

## What's Built

### Orchestra Repo (feat/hack branch) — 10 commits

| Commit | Description |
|--------|-------------|
| `fea1a58` | Poll tools (AI SDK + MCP): createPoll, getPollResults, votePoll, closePoll |
| `cbbcc3f` | Poll UI (MessagePoll.vue) + SDK votePoll with atomic arrayUnion/arrayRemove |
| `5ec7428` | LiveKit agent token endpoint (getAgentLiveKitToken) |
| `7197490` | External agent engine — webhook dispatch with full session context |
| `60f1bea` | Voice engine setting (ai_agent_voice_engine) + meeting join trigger for personal chats |
| `5c1d87b` | MCP passthrough in webhook payload + update_ai_message tool for response streaming |
| `645e49a` | Agent config UI: external engine fields, voice engine selector, Voice Call trigger |
| `a14fca1` | Review fixes: atomic votes, message auth check, server-side MCP key |
| `803fbce` | Server-generated JWT auth for external engine MCP access |
| `9480756` | Hide integrations config for external engine agents |
| `16cd9b5` | Error logging in executeUnified catch block |

### External Repo (frontier-tower-agent) — 6 commits

| Component | Files | Purpose |
|-----------|-------|---------|
| Voice Agent | `voice-agent/main.py` | Webhook server: receives triggers from Orchestra, handles text (Claude + MCP tools + streaming) and voice (LiveKit + STT + TTS) |
| MCP Client | `voice-agent/orchestra_client.py` | HTTP client for Orchestra MCP, authenticates via x-functions-auth JWT |
| Solana Tools | `voice-agent/solana_tools.py` | check_balance, transfer_sol, get_wallet_address |
| Metaplex | `solana/register-agent.ts` | On-chain agent registration script |
| Metaplex | `solana/agent-registration.json` | Agent metadata (ERC-8004 standard) |
| Prompts | `prompts/text-prompt.md` | Full agent instructions for Orchestra |
| Prompts | `prompts/voice-prompt.md` | Condensed voice interaction rules |
| Docs | `docs/architecture.md` | System architecture |
| Docs | `docs/demo-script.md` | 5 demo scenarios |
| Docs | `docs/unbrowse-setup.md` | Unbrowse integration guide |

---

## Architecture

```
Text @mention / DM ──► Orchestra trigger system ──► External engine webhook
Schedule trigger   ──►     (builds session context:     ──► Voice Agent Worker
Voice call         ──►      history, memories, prompt)       │
                                                             ├── Text: Claude LLM + MCP tools
                                                             │   → streams response to chat
                                                             ├── Voice: joins LiveKit room
                                                             │   → Deepgram STT → Claude → ElevenLabs TTS
                                                             └── Solana: wallet management
                                                                 → treasury, bounties, governance

Orchestra provides:              Voice Worker provides:
├── Agent identity               ├── LLM execution (Claude)
├── Session context & memory     ├── STT (Deepgram)
├── Trigger system               ├── TTS (ElevenLabs)
├── MCP tools (40+)              ├── Audio I/O (LiveKit)
├── Execution tracking           ├── Solana wallet
└── Workspace data               └── Webhook server
```

---

## TODO Before Submission

### Must Do
- [x] **Fix assistant bug** — unified error handling and thinking message lifecycle
- [ ] **Push external repo** — latest commits with JWT auth
- [ ] **Set up demo workspace** — 16 floor projects, channels, sample residents with descriptions
- [ ] **Test text agent** — @mention, polls, resource matching
- [ ] **Test voice agent** — run worker locally + tunnel, start call in personal chat
- [ ] **Run Metaplex registration** — fund devnet wallet, upload metadata to Arweave, run script
- [ ] **Record demo video** — backup for judges
- [ ] **Submit to DevSpot**

### Nice to Have
- [ ] Register on frontier.human.tech (human.tech bonus track)
- [ ] Configure Unbrowse as Direct MCP Application
- [ ] Set up Solana devnet wallet with test SOL

---

## Demo Scenarios

1. **Voice Onboarding** (~2 min): Call agent → welcome, interest discovery, add to channels
2. **Building Poll** (~1 min): "Vote on furniture?" → poll created → vote in UI → results
3. **Resource Matching** (~1 min): "Need ML expert" → search profiles → introduce
4. **Daily Digest** (scheduled): Activity summary + external events
5. **On-chain Identity** (~30 sec): Show Metaplex registration on Solana Explorer

---

## How to Run

### Voice Agent Worker (local)
```bash
cd voice-agent
pip install -r requirements.txt
cp .env.example .env.local
# Fill in: ANTHROPIC_API_KEY, ELEVEN_API_KEY (used for both STT and TTS)
# LIVEKIT_* keys (for voice calls)
# MCP credentials come from Orchestra webhook payload (auto)
python main.py
```

### Voice Agent Worker (Railway deployment)
```bash
# Install Railway CLI: brew install railway
railway login
railway init --name frontier-tower-agent
railway add -s voice-agent
railway service voice-agent

# Set env vars
railway variables set \
  ANTHROPIC_API_KEY=sk-ant-... \
  ELEVEN_API_KEY=sk_... \
  LIVEKIT_URL=wss://your-livekit.livekit.cloud \
  LIVEKIT_API_KEY=... \
  LIVEKIT_API_SECRET=... \
  ELEVENLABS_VOICE_ID=ODq5zmih8GrVes37Dizd \
  SOLANA_RPC_URL=https://api.devnet.solana.com \
  SOLANA_PRIVATE_KEY='[...keypair bytes...]'

# Deploy (from voice-agent/ directory)
cd voice-agent
railway up

# Get the public URL
railway domain
# → https://your-app.up.railway.app
# Webhook URL: https://your-app.up.railway.app/webhook
```

### Solana Wallet Setup
```bash
# 1. Generate a keypair (or use existing)
python3 -c "
from solders.keypair import Keypair
import json
kp = Keypair()
print('Address:', kp.pubkey())
print('Key JSON:', json.dumps(list(bytes(kp))))
"

# 2. Fund with devnet SOL
#    Go to https://faucet.solana.com
#    Paste the address, select Devnet, request 5 SOL

# 3. Set the key on Railway (or in .env.local for local dev)
railway variables set SOLANA_PRIVATE_KEY='[...the key JSON array...]'
```

### Metaplex Registration
```bash
cd solana
npm install
# Upload agent-registration.json to Arweave first
AGENT_REGISTRATION_URI=https://arweave.net/... npm run register
```

### Orchestra Agent Setup
1. Create agent blueprint in Orchestra
2. Set engine to "External", webhook URL: `https://your-app.up.railway.app/webhook`
3. Set voice engine to "External", same webhook URL
4. Enable triggers: mention, Voice Call
5. Deploy the agent

---

## Key Environment Variables

### Voice Worker (.env.local)
```
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
ANTHROPIC_API_KEY=sk-ant-...
DEEPGRAM_API_KEY=...
ELEVEN_API_KEY=sk_...
ELEVENLABS_VOICE_ID=ODq5zmih8GrVes37Dizd
WEBHOOK_PORT=8765
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_PRIVATE_KEY=[...]
```

### Orchestra Cloud Functions
```
MCP_SERVER_URL=https://...cloudfunctions.net/mcpServer
FUNCTIONS_JWT_SECRET=... (already set, used for JWT generation)
```

---

## Known Issues

1. ~~**Assistant bug**~~ — Fixed. Thinking message lifecycle and error handling unified.

2. **Emulator project mismatch** — local dev requires `.firebaserc` development alias to match the web app's projectId. Fixed by pointing development → orchestra-ai-test-2.
