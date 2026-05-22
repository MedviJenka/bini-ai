# Bini AI Service

A multi-modal AI agent service exposing vision, text, and speech-to-text capabilities via a REST API. Built with FastAPI, CrewAI, and Azure OpenAI.

---

## Architecture

```
backend/
  ai/
    agents/          # Five CrewAI agents (vision, text, stt, english, html)
    flows/           # CrewAI Flow state machines
    tools/           # Custom CrewAI tools (vision, STT, file)
    mcp/             # MCP manager and service
  api/v1/bini/       # FastAPI route handlers + request logic + schemas
  settings.py        # Pydantic Settings + LLMFactory (Azure OpenAI)
  utils/             # Logger, infrastructure base class, executor
client/
  bini.py            # BiniClient — REST client used by tests and consumers
services/
  bini.py            # FastAPI app entry point (Uvicorn, 4 workers)
tests/               # pytest + Allure, session-scoped Uvicorn fixture
```

### Agents

| Agent | Purpose |
|-------|---------|
| `vision_agent` | Image analysis + Pass/Fail validation via `BiniVisionTool` |
| `text_agent` | Text extraction and QA (two-task pipeline) |
| `stt_agent` | Speech-to-text via Azure Cognitive Services (hierarchical manager) |
| `english_agent` | Grammar correction — refines prompts inside the vision flow |
| `html_agent` | HTML parsing, extracts UI elements to CSV using Playwright |

### API Endpoints

| Method | Path | Input | Output |
|--------|------|-------|--------|
| POST | `/api/v1/bini/image` | multipart: `prompt`, `image`, optional `schema_output`, optional `sample_image[]` | plain text or structured JSON |
| POST | `/api/v1/bini/text` | JSON: `{ prompt, schema_output? }` | plain text or structured JSON |
| POST | `/api/v1/bini/audio` | multipart: `prompt`, `audio`, optional `schema_output` | plain text or structured JSON |

Pass `schema_output` (JSON Schema string for multipart, dict for JSON) to receive a structured response validated against your schema.

---

## Requirements

- Python 3.12
- [UV](https://github.com/astral-sh/uv) package manager
- Docker
- Azure OpenAI credentials (see `.env` setup below)

---

## Setup

**Install dependencies:**
```bash
uv sync
```

**Configure environment** — create a `.env` file at the repo root:
```
AZURE_API_KEY=...
AZURE_ENDPOINT=...
AZURE_API_VERSION=...
PORT=8081
ENV=development
```

---

## Running Locally

**With Docker Compose** (recommended for dev, maps port 9999 → 8081):
```bash
docker compose up -d --build
```

**Direct (no Docker):**
```bash
uv run python services/bini.py
```

---

## Testing

**Run all tests in parallel with Allure report:**
```bash
cd tests && pytest -n auto --dist=loadscope && allure serve results
```

**Run a single test file:**
```bash
cd tests && pytest test_image.py -n auto --dist=loadscope
```

**Run a single test by name:**
```bash
cd tests && pytest test_image.py::test_function_name
```

Tests spin up a session-scoped Uvicorn server on port 9999 and use `BiniClient` to hit the API.

---

## Deployment

### Build and Push to Azure Container Registry

```bash
az acr login --name biniai
docker build --target bini_service -t "biniai.azurecr.io/bini/bini-service:latest" -f Dockerfile .
docker push "biniai.azurecr.io/bini/bini-service:latest"
```

### Redeploy Production Stack

On the production VM, redeploy the Docker Swarm stack:

```bash
cd Bini
docker stack deploy -c stack.yaml bini --with-registry-auth
```

Production runs 3 replicas with rolling updates on an overlay network. A separate monitoring stack (`deploy.monitoring.yaml`) exposes Prometheus metrics.

---

## Client Usage

`BiniClient` is a dataclass-based HTTP client that wraps the REST API:

```python
from client.bini import BiniClient
from pydantic import BaseModel

client = BiniClient(host="localhost", port=9999)

# Plain text response
result = client.run_image(prompt="Describe this image", image="path/to/image.png")

# Structured response
class MySchema(BaseModel):
    passed: bool
    description: str

result = client.run_image(prompt="Did the test pass?", image="path/to/image.png", schema_output=MySchema)
# result is a dict matching MySchema
```
