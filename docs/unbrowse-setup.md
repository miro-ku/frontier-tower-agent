# Unbrowse Integration Setup

Unbrowse gives the Frontier Tower agent direct API access to external websites without browser automation — for event discovery, local services, and building news.

## How It Works

Orchestra's External Tools system supports Direct MCP integrations. Unbrowse is configured as a Direct MCP Application, and its tools are automatically merged with Orchestra's built-in tools at agent execution time.

## Setup Steps

### 1. Create an Unbrowse Application in Orchestra

In Orchestra workspace settings → Integrations:

1. Click **"Add Custom MCP Server"**
2. Configure:
   - **Name**: "Unbrowse"
   - **Integration type**: `mcp_direct`
   - **Server URL**: Your Unbrowse MCP endpoint (from [unbrowse.ai](https://unbrowse.ai))
   - **Auth type**: `api_key`
   - **Auth value**: Your Unbrowse API key

### 2. Enable on the Agent

In the Frontier Tower agent configuration:

1. Go to **Integrations** section
2. Enable the "Unbrowse" Application
3. Deploy the agent

### 3. Use in Agent Instructions

Add to the agent's description/instructions:

```
## External Data (Unbrowse)
When residents ask about external information, use Unbrowse tools to:
- Search for local events (Eventbrite, Luma, Meetup)
- Look up nearby restaurants and services
- Monitor tech news relevant to the building's community
- Pull data from building management portals
```

## What the Agent Can Do

Once configured, the agent automatically gets Unbrowse's tools (namespaced as `unbrowse__*`):

- **Search websites** — query any site's data without browser automation
- **Get structured data** — extract specific data from web pages
- **API access** — direct API calls using your browser session for auth

## Voice Agent Integration

The voice agent (`voice-agent/main.py`) can also use Unbrowse by adding it as an MCP tool in the LLM's function definitions. However, since Unbrowse is already available through Orchestra's integration system, the text-based agent handles it natively — no additional code needed.

For voice-specific Unbrowse access, add a tool to `main.py` that calls the Unbrowse API directly via HTTP.
