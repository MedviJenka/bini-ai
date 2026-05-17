# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run tests locally (from repo root):**
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

**Start dev server with Docker:**
```bash
docker compose up -d --build
```

**Build and push to Azure Container Registry:**
```bash
az acr login --name biniai
docker build --target bini_service -t "biniai.azurecr.io/bini/bini-service:latest" -f Dockerfile .
docker push "biniai.azurecr.io/bini/bini-service:latest"
```

**Redeploy production stack (on Ubuntu VM at 10.8.2.35):**
```bash
cd Bini && docker stack deploy -c stack.yaml bini --with-registry-auth
```

**Package manager:** UV (`uv sync` to install dependencies, defined in `pyproject.toml`). Requires Python 3.12.

## Architecture

### Overview

Bini is a **multi-modal AI agent service** that exposes vision, text, and speech-to-text capabilities via a REST API. The server runs on port 8081 (mapped to 9999 in dev Docker Compose).

### Agent Layer (`backend/ai/`)

Each agent lives in its own subdirectory under `backend/ai/agents/` with:
- `crew.py` — main entry point (async function called by the API)
- `flow.py` — CrewAI Flow state machine (where used)
- `config/agents.yaml` — agent role/goal/backstory definitions
- `config/tasks.yaml` — task descriptions and expected outputs

All agents extend `AgentInfrastructure` (`backend/utils/infrastructure.py`), which provides a shared `LLMFactory`-backed `llm` cached property. LLM is Azure OpenAI (configured via `AZURE_*` env vars in `.env`).

**Five agents:**
- `vision_agent` — image analysis + Pass/Fail validation, uses `BiniVisionTool`
- `text_agent` — text extraction and QA assistant (two-task pipeline)
- `stt_agent` — speech-to-text via Azure Cognitive Services, hierarchical manager pattern
- `english_agent` — grammar correction (used inside the vision flow to refine prompts)
- `html_agent` — HTML parsing, extracts UI elements to CSV using Playwright

**Flow pattern (CrewAI Flows):** Vision uses a flow (`backend/ai/agents/vision_agent/flow.py`) that sequences: refine prompt (english_agent) → analyze image (vision_agent). Text also has a flow with success/failure routing (`backend/ai/flows/text.py`).

### API Layer (`backend/api/v1/bini/`)

- `api.py` — FastAPI route handlers for `/image`, `/text`, `/audio`
  - `/image` and `/audio` use multipart form (`prompt`, file, optional `schema_output` JSON string)
  - `/text` uses JSON body (`{"prompt": str, "schema_output": dict | null}`)
- `logic.py` — helpers: `json_schema_to_pydantic()` converts JSON Schema dicts to Pydantic models at runtime; `save_temp_image()` / `save_temp_audio()` / `cleanup_files()` for file lifecycle
- `schemas.py` — request/response Pydantic models

**Image endpoint** accepts multipart form (`prompt`, `image`, optional `schema_output` JSON string, optional `sample_image` files). Text endpoint accepts JSON body. Both return `JSONResponse`.

### Configuration (`backend/settings.py`)

`Settings` (pydantic-settings, reads `.env`) — all env vars in one place. `LLMFactory` is a dataclass with a `@cached_property llm` that validates Azure env vars and constructs the CrewAI `LLM`. The global singletons are `Config = Settings()` and `TestConfig = TestSettings()`.

### Client Library (`client/bini.py`)

`BiniClient` is a dataclass-based REST client used in tests and by external consumers. It wraps `requests` and provides `run_image()`, `run_text()`, `run_audio()`, `run_video()` methods with multipart upload and schema serialization.

### Service Entry Point (`services/bini.py`)

FastAPI app with lifespan, CORS middleware, exception handlers. The router from `backend/api/v1/bini/api.py` is mounted here. In production, Uvicorn runs this with 4 workers.

### Tests (`tests/`)

Tests use a session-scoped fixture that starts a Uvicorn server on port 9999 and provides a `BiniClient` instance. Pytest config (`pytest.ini`) runs in async mode with Allure reporting (`--alluredir results --clean-alluredir`). Parallel execution via `pytest-xdist` (`-n auto --dist=loadscope`).

### Deployment

- **Dev:** `docker compose up` (single container, port 9999→8081)
- **Production:** Docker Swarm on Ubuntu VM (`10.8.2.35`), 3 replicas, rolling updates, overlay network
- **Image registry:** Azure Container Registry (`biniai.azurecr.io`)
- **Monitoring:** Separate Swarm stack (`deploy.monitoring.yaml`) with Prometheus middleware
