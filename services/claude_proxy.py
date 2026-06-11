"""
Claude Code Proxy v2 — OpenAI-compatible endpoint backed by the claude CLI.

Security contract:
- All user content travels via stdin (--input-format stream-json); never via CLI args.
- Bearer auth on every route except /health.
- Concurrency bounded by CLAUDE_PROXY_MAX_CONCURRENCY (default 4).
- Model names validated against CLAUDE_PROXY_MODEL_ALLOWLIST.
"""

from __future__ import annotations

import hmac
import json
import time
import uuid
import asyncio
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from settings import Config
from utils.logger import Logger

__all__ = ["app"]

log = Logger(name="claude-proxy")

# ------------------------------------------------------------------ #
#  Concurrency limiter — created once at module level                  #
# ------------------------------------------------------------------ #
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(Config.CLAUDE_PROXY_MAX_CONCURRENCY)
    return _semaphore


# ------------------------------------------------------------------ #
#  Pydantic models                                                     #
# ------------------------------------------------------------------ #

class _Msg(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class _ResponseFormat(BaseModel):
    type: str = "text"
    json_schema: dict[str, Any] | None = None


class _Req(BaseModel):
    model: str = "claude-sonnet-4-6"
    messages: list[_Msg] = []
    temperature: float | None = None
    max_tokens: int | None = None
    response_format: _ResponseFormat | None = None


# ------------------------------------------------------------------ #
#  Message translation                                                 #
# ------------------------------------------------------------------ #

def _translate_image_block(block: dict[str, Any]) -> dict[str, Any]:
    """Convert an OpenAI image_url block to a Claude image source block."""
    if block.get("type") != "image_url":
        return block

    url: str = (block.get("image_url") or {}).get("url", "")

    if url.startswith("data:"):
        # data:<media_type>;base64,<data>
        meta, _, data = url.partition(",")
        media_type = meta.split(":")[1].split(";")[0] if ":" in meta else "image/jpeg"
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data,
            },
        }

    # URL-referenced image — pass as url source
    return {
        "type": "image",
        "source": {
            "type": "url",
            "url": url,
        },
    }


def _translate_content(content: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    """Translate a single message content from OpenAI format to Claude format."""
    if isinstance(content, str):
        return content
    return [
        _translate_image_block(block) if block.get("type") == "image_url" else block
        for block in content
    ]


def _flatten_text(content: list[dict[str, Any]]) -> str:
    """Extract all text from a multi-part content block."""
    return " ".join(
        block.get("text", "") for block in content if block.get("type") == "text"
    )


def _translate_messages(
    messages: list[_Msg],
) -> tuple[str | None, list[dict[str, Any]]]:
    """
    Separate the system prompt and convert remaining messages to Claude
    stream-json input records.

    Returns:
        system_prompt: concatenated system text (or None)
        claude_messages: list of stream-json message objects
    """
    system_parts: list[str] = []
    claude_messages: list[dict[str, Any]] = []

    for msg in messages:
        if msg.role == "system":
            text = (
                msg.content
                if isinstance(msg.content, str)
                else _flatten_text(msg.content)
            )
            system_parts.append(text)
        elif msg.role == "user":
            claude_messages.append(
                {
                    "type": "user_message",
                    "content": _translate_content(msg.content),
                }
            )
        elif msg.role == "assistant":
            claude_messages.append(
                {
                    "type": "assistant_message",
                    "content": _translate_content(msg.content),
                }
            )

    system_prompt = "\n\n".join(system_parts) if system_parts else None
    return system_prompt, claude_messages


# ------------------------------------------------------------------ #
#  CLI command builder                                                 #
# ------------------------------------------------------------------ #

def _build_cli_args(
    model: str,
    system_prompt: str | None,
    json_schema: dict[str, Any] | None,
) -> list[str]:
    """
    Build the claude CLI command.  User content is NEVER passed as a CLI arg —
    it is streamed via stdin using --input-format stream-json.
    """
    cmd: list[str] = [
        "claude",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
        "--no-session-persistence",
    ]

    if system_prompt is not None:
        cmd += ["--system-prompt", system_prompt]

    if json_schema is not None:
        cmd += ["--json-schema", json.dumps(json_schema)]

    return cmd


# ------------------------------------------------------------------ #
#  Subprocess invocation                                               #
# ------------------------------------------------------------------ #

async def _invoke_cli(cmd: list[str], stdin_payload: bytes, timeout: int) -> bytes:
    """
    Spawn the claude CLI, pipe stdin_payload to it, and return stdout bytes.

    Raises HTTPException on timeout (504), nonzero exit (502), or oversized
    output (413).
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, _stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_payload), timeout=timeout
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise HTTPException(504, "Claude CLI timed out")

    if proc.returncode != 0:
        # Deliberately do NOT leak stderr to the caller
        raise HTTPException(502, "Claude CLI returned a non-zero exit code")

    max_bytes = 32 * 1024 * 1024  # 32 MB guard
    if len(stdout) > max_bytes:
        raise HTTPException(413, "Response from CLI exceeds size limit")

    return stdout


# ------------------------------------------------------------------ #
#  Output parsing                                                      #
# ------------------------------------------------------------------ #

def _parse_stream_json(stdout: bytes, has_schema: bool) -> dict[str, Any]:
    """
    Scan stdout lines for the stream-json result event.

    Returns a dict with keys: result, structured_output, usage.
    Raises HTTPException(502) if no valid result line is found.
    """
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("type") == "result":
            if obj.get("is_error"):
                raise HTTPException(502, "Claude CLI reported an error in result")

            usage = obj.get("usage") or {}
            return {
                "result": obj.get("result", ""),
                "structured_output": obj.get("structured_output") if has_schema else None,
                "usage": {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                },
            }

    raise HTTPException(502, "No result line found in CLI output")


# ------------------------------------------------------------------ #
#  Core completion logic                                               #
# ------------------------------------------------------------------ #

async def _complete(req: _Req) -> dict[str, Any]:
    model = req.model.removeprefix("openai/")

    allowlist = [m.strip() for m in Config.CLAUDE_PROXY_MODEL_ALLOWLIST.split(",")]
    if model not in allowlist:
        raise HTTPException(422, f"Model '{model}' is not in the allowlist")

    json_schema: dict[str, Any] | None = None
    if req.response_format and req.response_format.type == "json_schema":
        json_schema = req.response_format.json_schema

    system_prompt, claude_messages = _translate_messages(req.messages)
    cmd = _build_cli_args(model, system_prompt, json_schema)
    stdin_lines = "\n".join(json.dumps(m) for m in claude_messages).encode()

    sem = _get_semaphore()
    if sem._value == 0:  # noqa: SLF001  — asyncio Semaphore has no public peek
        raise HTTPException(429, "Too many concurrent requests")

    async with sem:
        stdout = await _invoke_cli(cmd, stdin_lines, Config.CLAUDE_PROXY_TIMEOUT)

    parsed = _parse_stream_json(stdout, has_schema=json_schema is not None)

    content: str = parsed["result"]
    if parsed["structured_output"] is not None:
        content = json.dumps(parsed["structured_output"])

    usage = parsed["usage"]
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {
            "prompt_tokens": usage["input_tokens"],
            "completion_tokens": usage["output_tokens"],
            "total_tokens": usage["input_tokens"] + usage["output_tokens"],
        },
    }


# ------------------------------------------------------------------ #
#  FastAPI application                                                 #
# ------------------------------------------------------------------ #

app = FastAPI(title="Claude Code Proxy v2")


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):  # type: ignore[type-arg]
    """Validate Bearer token for all routes except /health."""
    if request.url.path == "/health":
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401, content={"detail": "Missing Bearer token"}
        )

    token = auth_header[len("Bearer "):]
    if not token or not hmac.compare_digest(token, Config.MCP_PROXY_AUTH_TOKEN):
        return JSONResponse(
            status_code=401, content={"detail": "Invalid Bearer token"}
        )

    return await call_next(request)


@app.post("/v1/chat/completions")
async def chat_completions(req: _Req) -> dict:  # type: ignore[type-arg]
    return await _complete(req)


@app.get("/v1/models")
async def list_models() -> dict:  # type: ignore[type-arg]
    models = [
        {"id": m.strip(), "object": "model", "owned_by": "anthropic"}
        for m in Config.CLAUDE_PROXY_MODEL_ALLOWLIST.split(",")
    ]
    return {"object": "list", "data": models}


@app.get("/health")
async def health() -> dict:  # type: ignore[type-arg]
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8787)
