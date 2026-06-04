# Bini AI

A vision-focused AI agent exposed as an MCP server. Built with FastMCP, CrewAI, and Anthropic Claude.

---

## Architecture

```
main.py                          # FastMCP server entry point (streamable-http, port 6000)
backend/
  ai/
    agents/vision_agent/
      crew.py                    # ComputerVisionAgent — CrewAI crew (analysis + decision)
      flow.py                    # VisionFlow — retry loop with confidence gating
      schemas.py                 # Structured output schemas (VisionSchema, QAObservation)
      config/                    # YAML agent/task definitions
    tools/
      vision_tool.py             # BiniVisionTool — image encoding, resize, LLM call
      stt.py                     # STTTool — Azure Speech-to-Text
      file_tool.py               # File read/write/list tools
  functions/
    common.py                    # MCP client helper (Python, FastMCP Client)
    common.ts                    # MCP client helper (TypeScript, MCP SDK)
  settings.py                    # Pydantic Settings + LLMFactory (Anthropic Claude)
  paths.py                       # Project root path resolution
  utils/
    logger.py                    # Logfire-based structured logging
    infrastructure.py            # AgentInfrastructure base class for CrewAI agents
tests/                           # pytest + Allure
```

### MCP Tool

The server exposes a single tool:

| Tool | Parameters | Returns |
|------|------------|---------|
| `Vision` | `prompt` (str), `image` (str), optional `sample_image` (list[str]) | Structured dict with visual attributes, comparison findings, and a Pass/Fail decision |

The vision agent runs a two-stage CrewAI pipeline — an image analysis agent extracts visual attributes, then a decision agent validates requirements. A `VisionFlow` wraps this with confidence-based retries (up to 3 attempts, minimum 95% confidence).

---

## Requirements

- Python >=3.12, <3.13
- [UV](https://github.com/astral-sh/uv) package manager
- Docker (optional)
- Anthropic API key

---

## Setup

**Install dependencies:**
```bash
uv sync
```

**Configure environment** — create a `.env` file at the repo root:
```
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=...
LOGFIRE_TOKEN=...
MCP_PROXY_AUTH_TOKEN=...
ENV=development
VERBOSE=false
```

---

## Running Locally

**With Docker Compose** (MCP service on port 6000, MCP Inspector dashboard on port 6274):
```bash
docker compose up -d --build
```

**Direct (no Docker):**
```bash
uv run fastmcp run main.py:mcp --transport streamable-http --host 0.0.0.0 --port 6000
```

---

## Testing

**Run all tests with Allure report:**
```bash
cd tests && pytest && allure serve results
```

**Run a single test file:**
```bash
cd tests && pytest test_image.py
```

**Run a single test by name:**
```bash
cd tests && pytest test_image.py::test_function_name
```

---

## Deployment

### Build and Push to Azure Container Registry

```bash
az acr login --name biniai
docker buildx bake --push
```

Or manually:
```bash
docker build --target mcp_service -t "biniai.azurecr.io/bini/bini-service:latest" -f Dockerfile .
docker push "biniai.azurecr.io/bini/bini-service:latest"
```

---

## Client Usage

**Python (FastMCP Client):**
```python
from fastmcp import Client

client = Client("http://localhost:6000/mcp")
async with client:
    result = await client.call_tool("Vision", {
        "prompt": "Describe this image",
        "image": "<base64-encoded image>",
    })
```

**TypeScript (MCP SDK):**
```typescript
import { Client } from "@modelcontextprotocol/sdk/client";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const client = new Client({ name: "bini-client", version: "1.0.0" });
await client.connect(new StreamableHTTPClientTransport(new URL("http://localhost:6000/mcp")));
const result = await client.callTool({ name: "Vision", arguments: { prompt: "Describe this image", image: "<base64>" } });
```
