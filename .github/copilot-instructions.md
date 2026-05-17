# Project Guidelines

## Architecture

- Bini is a FastAPI service that exposes multimodal AI endpoints under `/api/v1/bini`; the app entrypoint is `services/bini.py` and the route handlers live in `backend/api/v1/bini/api.py`.
- Treat `backend/ai/agents/` as the agent layer. Each agent keeps its own `crew.py`, optional `flow.py`, and `config/agents.yaml` plus `config/tasks.yaml`.
- Reuse `AgentInfrastructure` in `backend/utils/infrastructure.py` for CrewAI-based agents instead of wiring LLM instances ad hoc.
- Keep API request and response contracts aligned with the existing split: `/image` and `/audio` use multipart form data, `/text` uses JSON body.
- The frontend in `frontend/app/` is a separate Create React App project. Do not assume frontend changes are required for backend tasks.
- See `CLAUDE.md` for the fuller architecture overview and deployment notes.

## Build and Test

- Use Python 3.12 and `uv` for Python dependency management. Install dependencies with `uv sync` from the repo root.
- Start the local containerized service with `docker compose up -d --build`. The container serves port `8081` and the dev compose maps it to `9999`.
- Run tests from the `tests/` directory, not the repo root. Prefer `pytest -n auto --dist=loadscope` for the suite or a single file.
- The test configuration writes Allure results into `tests/results` or `results` depending on the command flow; avoid committing generated report artifacts.
- See `CLAUDE.md` for the canonical test and deployment commands.

## Conventions

- Keep runtime configuration in `backend/settings.py`; new environment variables should be defined there rather than read directly from `os.environ` in feature code.
- Preserve the versioned API prefix pattern by building routes from `Config.API_VERSION` instead of hardcoding `/v1` in multiple places.
- When an endpoint accepts `schema_output`, preserve the current behavior: validate the schema early, then return either structured JSON or a string wrapper consistent with the existing endpoint.
- Temporary upload files are managed through helpers in `backend/api/v1/bini/logic.py`; reuse them instead of open-coded file lifecycle handling.
- The Python client in `client/bini.py` is the reference for external API usage and is exercised by tests. Keep server changes compatible with it unless the task explicitly changes the client contract.
- For frontend work, follow the existing React + TypeScript app structure in `frontend/app/src/` and use `frontend/app/README.md` for CRA-specific commands.