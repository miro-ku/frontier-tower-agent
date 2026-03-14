# Demo Script

Five scenarios demonstrating the Frontier Tower Agent's capabilities. Total demo time: ~6 minutes.

---

## Scenario 1: Voice Onboarding (~2 min)

**Setup**: Join a LiveKit room where the voice agent is active.

**Script**:
1. Agent greets: *"Hey! Welcome to Frontier Tower. I'm your building concierge. How can I help?"*
2. Say: *"Hi, I just moved in. I'm on floor 7 and I work in robotics."*
3. Agent responds, asks about specific interests
4. Say: *"I'm interested in humanoid robots and computer vision."*
5. Agent:
   - Searches member profiles for robotics/CV residents
   - Introduces 2-3 matches: *"There are a few people you should meet — Alex on floor 3 works on manipulation systems, and Sarah on floor 12 does computer vision research."*
   - Offers to add to relevant channels
6. Say: *"Yes, add me to the events channel."*
7. **Show**: Orchestra UI updating in real-time — member added to channel

**Demonstrates**: Voice interaction, member search, resource matching, channel management

---

## Scenario 2: Building Poll (~1 min)

**Script** (text or voice):
1. Say/type: *"Can we run a poll about the new common area furniture? Options: modern minimalist, cozy lounge, and standing desks."*
2. Agent confirms and creates poll
3. **Show**: Orchestra UI — poll message appears in the channel with three options
4. **Click**: Vote on an option in the UI
5. Say: *"What are the poll results so far?"*
6. Agent reads and announces current tally

**Demonstrates**: Poll creation, UI rendering, voting, results retrieval

---

## Scenario 3: Resource Matching (~1 min)

**Script**:
1. Say: *"I need someone who knows about machine learning for a project I'm working on."*
2. Agent searches member profiles
3. Agent responds: *"I found 3 residents with ML expertise — Jordan on floor 4 specializes in reinforcement learning, Pat on floor 9 does NLP, and Chris on floor 2 works on generative models. Want me to introduce you to any of them?"*
4. Say: *"Introduce me to Jordan."*
5. Agent sends a DM to Jordan with the introduction

**Demonstrates**: Member profile search, cross-floor matching, DM capability

---

## Scenario 4: Daily Digest (scheduled, ~1 min)

**Show**: A pre-generated daily digest message in the Building Announcements channel:

```
📊 Frontier Tower Daily Digest — March 14, 2026

🆕 Activity
- 12 tasks created across 6 floors
- 4 tasks completed
- 3 new residents joined

💬 Active Discussions
- Floor 5: Robotics lab equipment sharing (15 messages)
- Governance: Parking allocation proposal (8 messages)
- Events: Friday mixer planning (6 messages)

📅 Upcoming
- Friday Mixer — Floor 1 Common Area, 6pm
- Governance Vote: Common area renovation closes Sunday
```

**Demonstrates**: Activity summary, scheduled triggers, cross-floor visibility

---

## Scenario 5: On-chain Identity (~30 sec)

1. **Show**: Solana Explorer with the agent's registered identity
2. Point out:
   - MPL Core asset with AgentIdentity plugin
   - Agent registration document (name, description, MCP endpoint)
   - PDA wallet address
3. Explain: *"The agent has an on-chain identity on Solana via Metaplex. This enables verifiable agent identity, discoverability, and future payment capabilities for premium concierge services."*

**Demonstrates**: Metaplex Agent Registry integration, on-chain identity
