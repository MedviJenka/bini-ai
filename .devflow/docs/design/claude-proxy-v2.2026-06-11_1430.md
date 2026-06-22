---
type: design-artifact
version: 1
status: APPROVED
title: "Claude Code Proxy v2: Multimodal, Structured Output, Auth, Hardening"
slug: claude-proxy-v2
created: 2026-06-11T14:30:00Z
execution-strategy: SEQUENTIAL_CODERS
context-risk: HIGH
---

## 1. Problem Statement

The Claude Code proxy server (`services/claude_proxy.py`) wraps the `claude` CLI binary behind an OpenAI-compatible endpoint so CrewAI agents can use Claude without a direct API key. The current 88-line implementation has critical limitations:

- **Multimodal broken**: `_Msg.content: str` rejects image content blocks — all vision requests fail with 422
- **Structured output broken**: No `--json-schema` support — VisionSchema Pydantic output is unreliable
- **No authentication**: Port 8787 is open to any caller with access to the Docker network
- **No concurrency control**: Each request spawns a Node.js subprocess with no limits
- **Command injection risk**: User-controlled strings passed as CLI arguments
- **ARG_MAX violations**: Base64 images (2-4MB) exceed OS argument length limits

Target users: CrewAI vision agents (image_analysis_agent, decision_agent), MCP tool consumers, HTTP API consumers.

## 2. Acceptance Criteria

- [ ] Multimodal messages (text + base64 images) pass through the proxy to Claude CLI and return correct responses
- [ ] VisionSchema structured output is validated via `--json-schema` and returned in `choices[0].message.content`
- [ ] All dynamic content (prompts, images) flows via stdin, never as CLI arguments
- [ ] Bearer token auth validates against `MCP_PROXY_AUTH_TOKEN`; `/health` exempt
- [ ] Concurrent requests beyond limit return HTTP 429 with `Retry-After` header
- [ ] Malformed CLI output returns 502 (not 500 crash); stderr never leaked to clients
- [ ] Docker container runs as non-root with resource limits and `no-new-privileges`
- [ ] All existing text-only requests continue to work (backward compatible)
- [ ] 30+ unit tests covering text, multimodal, auth, concurrency, and error paths

## 3. Scope

**v1 Included:**
- Multimodal content model (`content: str | list[dict]`)
- Stream-json stdin/stdout for all requests (uniform code path)
- OpenAI → Claude image format translation at proxy boundary
- Structured output via `--json-schema` → `structured_output` field extraction
- Bearer auth middleware (MCP_PROXY_AUTH_TOKEN)
- asyncio.Semaphore concurrency limiter
- Error taxonomy (422/429/502/504) with sanitized messages
- Audit logging via Logger/Logfire
- Docker hardening (non-root, resource limits, security_opt)

**Deferred:**
- Session management (`--session-id`) — CrewAI handles inter-task context internally
- Streaming API (SSE) — not needed for current consumers
- Subprocess pooling — production fix priority, optimize later
- Custom tool definitions — CLI `--tools` only accepts built-in names; CrewAI uses text-based fallback
- VisionFlow retry backoff — outside proxy scope

**Excluded:**
- Direct Anthropic SDK integration (constraint: no API key)
- OpenAI streaming protocol (`stream: true`)
- MCP server tool passthrough

## 4. Gap Analysis Results

### Blocking Gaps (resolved in plan)

| Gap | Severity | Resolution |
|-----|----------|-----------|
| Command injection via CLI args | CRITICAL (99%) | All dynamic content via stdin; model validated against allowlist |
| No auth on endpoint | CRITICAL (97%) | Bearer token validation via MCP_PROXY_AUTH_TOKEN |
| Multimodal content can't be forwarded | CRITICAL (99%) | Stream-json stdin with format translation |
| Unbounded subprocess concurrency | CRITICAL (99%) | asyncio.Semaphore with configurable limit |
| Structured output contract undefined | CRITICAL (90%) | `--json-schema` flag, extract `structured_output` from result |
| ARG_MAX for base64 images | CRITICAL (99%) | Always stdin, never CLI args for content |
| Tool calling round-trip undefined | CRITICAL (92%) | Omit `--tools`; CrewAI handles via text fallback |

### Should-Address (mitigated in plan)

| Gap | Severity | Mitigation |
|-----|----------|-----------|
| Error recovery unspecified | HIGH | Error taxonomy: 422/429/502/504 with sanitized messages |
| Stream-json parse failure path | HIGH | Return 502 if no result line; 504 for truncated streams |
| Stdin delivery failures | HIGH | Max 10MB payload; `proc.communicate()` with timeout; BrokenPipeError → 502 |
| No audit logging | MEDIUM | Logger(name='claude-proxy') with Logfire |
| Docker runs as root | MEDIUM | Non-root user + security_opt + resource limits |
| .env not in .dockerignore | MEDIUM | Add to .dockerignore |

## 5. Execution Strategy

**SEQUENTIAL_CODERS** — 2 phases, single developer.

Phase 1 (Infrastructure) runs first because Phase 2 imports config from settings.py. Phase 2 is a single coder because TDD red-green-refactor requires one context for the tightly coupled proxy code + tests.

## 6. Subtask Breakdown

| Phase | Domain | Files | Depends On |
|-------|--------|-------|------------|
| 1 | Infrastructure | `settings.py`, `Dockerfile`, `compose.yaml` | — |
| 2 | Core + Tests (TDD) | `services/claude_proxy.py`, `tests/test_proxy_unit.py`, `tests/test_proxy_auth.py`, `tests/test_proxy_concurrency.py`, `tests/test_proxy_integration.py`, `pyproject.toml` | Phase 1 |

## 7. Implementation Plan

### Phase 1: Infrastructure Foundation

**Step 1a — Add proxy config to settings.py**

Add to the `Settings` class:
```python
CLAUDE_PROXY_MAX_CONCURRENCY: int = Field(default=4)
CLAUDE_PROXY_TIMEOUT: int = Field(default=300)
CLAUDE_PROXY_MODEL_ALLOWLIST: str = Field(default="claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-6")
```

`MCP_PROXY_AUTH_TOKEN` already exists (line 18). No change needed.

**Step 1b — Dockerfile non-root user**

In the `claude_proxy` stage:
```dockerfile
RUN useradd --create-home --shell /bin/bash proxy
USER proxy
```

**Step 1c — compose.yaml hardening**

```yaml
claude_proxy:
  env_file: [.env]
  volumes: [~/.claude:/home/proxy/.claude:ro]
  read_only: true
  tmpfs: [/tmp:size=100M]
  security_opt: [no-new-privileges:true]
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '2.0'
        pids: 32
```

Also add `.env` to `.dockerignore`.

### Phase 2: Core Rewrite + Tests (TDD)

**Step 2a — Rewrite models**
- `_Msg.content: str | list[dict[str, Any]]`
- `_Req`: add `response_format: dict | None = None`
- Model field validator: check against `Config.CLAUDE_PROXY_MODEL_ALLOWLIST`
- Return 422 with allowed models list on invalid model

**Step 2b — Rewrite _complete() with decomposed functions**

Per design review, decompose into 4 focused functions:

1. `_translate_messages(messages: list[_Msg]) -> list[dict]`
   - Separate system messages (→ `--system-prompt`)
   - Convert OpenAI `image_url` blocks to Claude `image` source format:
     - Parse `data:image/jpeg;base64,{data}` → `{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "{data}"}}`
   - Convert remaining text blocks
   - Return list of stream-json input objects: `{"type": "user_message", "content": ...}`

2. `_build_cli_args(model: str, system_prompt: str | None, json_schema: dict | None) -> list[str]`
   - Base: `["claude", "-p", "--verbose", "--input-format", "stream-json", "--output-format", "stream-json", "--model", model, "--no-session-persistence"]`
   - Add `--system-prompt` if present
   - Add `--json-schema` if response_format contains json_schema
   - No user content in args (security)

3. `_invoke_cli(cmd: list[str], stdin_payload: bytes, timeout: int) -> bytes`
   - `asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)`
   - `proc.communicate(input=stdin_payload)` with `asyncio.wait_for(timeout)`
   - Kill on timeout → raise HTTPException(504)
   - Non-zero exit → raise HTTPException(502, sanitized message)
   - Return stdout bytes

4. `_parse_stream_json(stdout: bytes, has_schema: bool) -> dict`
   - Split stdout by newlines, parse each as JSON
   - Find line with `"type": "result"`
   - If not found → raise HTTPException(502, "No result in CLI output")
   - Extract `structured_output` (if has_schema) or `result`
   - Extract `usage` tokens
   - Return parsed data dict

5. `_complete()` orchestrates: translate → build args → invoke → parse → return OpenAI response envelope

**Step 2c — Add Bearer auth middleware**
```python
async def _verify_auth(authorization: str = Header(alias="Authorization")) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    token = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(token, Config.MCP_PROXY_AUTH_TOKEN):
        raise HTTPException(401, "Invalid token")
```
Apply to `/v1/chat/completions` and `/v1/models`. Exempt `/health`.

Update `LLMFactory.llm` in settings.py: `api_key=Config.MCP_PROXY_AUTH_TOKEN`.

**Step 2d — Add concurrency limiter**
```python
_semaphore: asyncio.Semaphore  # initialized in lifespan

async def _complete(...):
    try:
        async with asyncio.timeout(5):
            await _semaphore.acquire()
    except TimeoutError:
        raise HTTPException(429, headers={"Retry-After": "10"})
    try:
        # ... invoke CLI
    finally:
        _semaphore.release()
```

Initialize in FastAPI lifespan from `Config.CLAUDE_PROXY_MAX_CONCURRENCY`.

**Step 2e — Error handling + logging**

Import `Logger(name="claude-proxy")`. Add structured logging for:
- Request: model, message count, has_images, has_schema
- Response: status, latency_ms, tokens
- Errors: full context logged server-side, sanitized message to client

Error taxonomy:
| Condition | HTTP Status | Message |
|-----------|-------------|---------|
| Invalid model | 422 | "Model not in allowlist" |
| Invalid content format | 422 | "Invalid content block" |
| Missing/bad auth | 401 | "Invalid token" |
| Semaphore full | 429 | "Too many concurrent requests" |
| CLI non-zero exit | 502 | "Claude CLI error" |
| No result in output | 502 | "No result in CLI output" |
| Malformed JSON output | 502 | "CLI returned invalid output" |
| CLI timeout | 504 | "Claude CLI timed out" |
| Payload too large | 413 | "Request payload exceeds 10MB" |

## 8. Patterns to Follow

| Pattern | Location | Usage |
|---------|----------|-------|
| Pydantic BaseSettings singleton | `settings.py:34` (`Config = Settings()`) | Import Config for all proxy settings |
| Logger with Logfire | `utils/logger.py` | `log = Logger(name="claude-proxy")` |
| FastAPI Depends for auth | Standard FastAPI pattern | Bearer token validation |
| Class-based pytest | `tests/test_vision.py` | TestProxyText, TestProxyMultimodal, etc. |
| asyncio_mode = auto | `tests/pytest.ini` | All async tests auto-detected |
| Field descriptions + Literal types | `ai/agents/vision_agent/schemas.py` | _Msg, _Req model definitions |

## 9. Integration Points

| Boundary | From | To | Format |
|----------|------|-----|--------|
| CrewAI → Proxy | LLM.call(messages=...) | POST /v1/chat/completions | OpenAI chat completion (multimodal content, response_format) |
| Proxy → CLI | _build_cli_args + _invoke_cli | claude -p stdin | Stream-json: `{"type":"user_message","content":...}` per line |
| CLI → Proxy | stdout | _parse_stream_json | Stream-json lines, find `type: "result"` |
| Proxy → CrewAI | HTTP response | LLM result | OpenAI chat.completion envelope |
| Settings → Proxy | Config singleton | Import | Auth token, concurrency limit, model allowlist |
| Settings → LLMFactory | Config.MCP_PROXY_AUTH_TOKEN | api_key parameter | Bearer token for proxy auth |

## 10. Design Review Results

| Anti-Pattern | Severity | Finding | Mitigation |
|-------------|----------|---------|-----------|
| God Functions | HIGH | `_complete()` had 5+ responsibilities | Decomposed into 4 focused functions + orchestrator |
| Error Handling | HIGH | Stream-json parse failure unspecified | 502 if no result line; log discarded lines |
| Error Handling | HIGH | Stdin delivery failures unspecified | Max 10MB; proc.communicate with timeout; BrokenPipeError → 502 |
| Poor Decomposition | MEDIUM | Auth + limiter in one file | Acceptable for v1 (<300 lines); split later if needed |
| Error Handling | MEDIUM | Model rejection behavior unspecified | 422 with allowed models list; empty allowlist = allow all |
| Missing Parallelism | MEDIUM | Sequential phases miss some parallelism | Accepted for simplicity — single developer |

## 11. Risk Assessment

**Context risk: HIGH** — Multimodal format translation + stream-json I/O + concurrency + auth + error recovery

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Stream-json format changes between CLI versions | MEDIUM | Parse defensively, validate result line exists, log unparsed lines |
| Image format translation bugs | HIGH | 4 dedicated multimodal tests + base64 passthrough validation |
| Semaphore race conditions | HIGH | asyncio.Semaphore is event-loop safe; test with concurrent requests |
| Non-root Docker permission issues | LOW | Test volume mount with compose up; document user/group setup |
| CrewAI tool calling via text fallback | MEDIUM | Already the current behavior; no regression |

## 12. PR Description Guidance

### Problem Being Solved
The Claude Code proxy server cannot handle multimodal content, has no authentication, no concurrency limits, and is vulnerable to command injection — making it unreliable for CrewAI vision agents that need structured Pydantic output from image analysis.

### Key Changes to Highlight
- Proxy now accepts multimodal messages (text + base64 images) via OpenAI format
- All dynamic content flows through stdin (not CLI args) for security
- Structured output via `--json-schema` returns validated JSON matching VisionSchema
- Bearer token auth using existing MCP_PROXY_AUTH_TOKEN
- Concurrency limiter prevents subprocess fork-bombing (default: 4 concurrent)
- Docker container hardened: non-root user, resource limits, no-new-privileges

### Breaking Changes
- POST `/v1/chat/completions` now requires `Authorization: Bearer <token>` header
- LLMFactory.api_key changes from `'claude-proxy'` to `Config.MCP_PROXY_AUTH_TOKEN`

### Reviewer Focus Areas
- `_translate_messages()`: OpenAI → Claude image format translation correctness
- `_parse_stream_json()`: Robustness of stream-json output parsing
- Auth middleware: timing-safe comparison, health endpoint exemption
- Concurrency limiter: semaphore release in error paths
