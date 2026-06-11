"""
Unit tests for the Claude Code Proxy v2.

Covers: text messages, multimodal image translation, structured output,
        and error-handling paths.
"""

from __future__ import annotations

import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from httpx import AsyncClient, ASGITransport

# ---------------------------------------------------------------------------
# Default mock subprocess result (stream-json format)
# ---------------------------------------------------------------------------
MOCK_RESULT = (
    b'{"type":"result","subtype":"success","is_error":false,'
    b'"result":"test response","usage":{"input_tokens":10,"output_tokens":20},'
    b'"stop_reason":"end_turn"}\n'
)

VALID_TOKEN = "test-secret-token"


def _make_mock_proc(stdout: bytes = MOCK_RESULT, returncode: int = 0) -> MagicMock:
    """Build a mock asyncio subprocess that returns the given stdout."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.kill = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    return proc


def _patch_proc(proc: MagicMock):
    return patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    )


def _patch_config(**overrides):
    """Patch Config values for isolation."""
    defaults = {
        "MCP_PROXY_AUTH_TOKEN": VALID_TOKEN,
        "CLAUDE_PROXY_MAX_CONCURRENCY": 4,
        "CLAUDE_PROXY_TIMEOUT": 300,
        "CLAUDE_PROXY_MODEL_ALLOWLIST": "claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-6",
    }
    defaults.update(overrides)
    return patch.multiple("services.claude_proxy.Config", **defaults)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(app) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )


# ---------------------------------------------------------------------------
# TestCompleteTextMessages
# ---------------------------------------------------------------------------

class TestCompleteTextMessages:
    """Verify plain-text message flow end to end."""

    @pytest.mark.asyncio
    async def test_basic_text_response_shape(self):
        """Response body matches OpenAI chat completion shape."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "Hello"}],
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "chat.completion"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["choices"][0]["message"]["content"] == "test response"
        assert body["usage"]["prompt_tokens"] == 10
        assert body["usage"]["completion_tokens"] == 20
        assert body["usage"]["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_system_prompt_passed_as_cli_arg(self):
        """System message becomes --system-prompt CLI arg, not stdin content."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc) as mock_exec, _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [
                            {"role": "system", "content": "You are a tester"},
                            {"role": "user", "content": "Hello"},
                        ],
                    },
                )

        call_args = mock_exec.call_args[0]
        assert "--system-prompt" in call_args
        idx = list(call_args).index("--system-prompt")
        assert call_args[idx + 1] == "You are a tester"

    @pytest.mark.asyncio
    async def test_user_content_not_in_cli_args(self):
        """User message content must NOT appear as a CLI positional argument."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc) as mock_exec, _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [
                            {"role": "user", "content": "secret user content"}
                        ],
                    },
                )

        call_args = list(mock_exec.call_args[0])
        assert "secret user content" not in call_args

    @pytest.mark.asyncio
    async def test_input_format_stream_json_flag(self):
        """CLI must use --input-format stream-json."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc) as mock_exec, _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )

        call_args = list(mock_exec.call_args[0])
        assert "--input-format" in call_args
        idx = call_args.index("--input-format")
        assert call_args[idx + 1] == "stream-json"

    @pytest.mark.asyncio
    async def test_model_passthrough(self):
        """Response echoes back the requested model."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-haiku-4-6",
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )

        assert resp.json()["model"] == "claude-haiku-4-6"

    @pytest.mark.asyncio
    async def test_openai_prefix_stripped(self):
        """openai/ prefix is stripped when passed to the CLI."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc) as mock_exec, _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "openai/claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )

        call_args = list(mock_exec.call_args[0])
        idx = call_args.index("--model")
        assert call_args[idx + 1] == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# TestCompleteMultimodalMessages
# ---------------------------------------------------------------------------

class TestCompleteMultimodalMessages:
    """Verify image_url → Claude image source translation."""

    @pytest.mark.asyncio
    async def test_base64_image_translated_to_claude_format(self):
        """image_url with data: URI is converted to Claude's base64 source format."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        captured_stdin: list[bytes] = []

        async def _fake_exec(*args, **kwargs):
            p = _make_mock_proc()
            # Capture stdin by wrapping communicate
            original_communicate = p.communicate

            async def _capture_communicate(input=None):
                if input is not None:
                    captured_stdin.append(input)
                return await original_communicate(input=input)

            p.communicate = _capture_communicate
            return p

        with patch("asyncio.create_subprocess_exec", new=_fake_exec), _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Describe this"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": "data:image/jpeg;base64,/9j/abc123"
                                        },
                                    },
                                ],
                            }
                        ],
                    },
                )

        assert captured_stdin, "stdin was never written"
        stdin_text = captured_stdin[0].decode()
        msg_obj = json.loads(stdin_text.strip().splitlines()[0])
        blocks = msg_obj["content"]
        image_block = next(b for b in blocks if b.get("type") == "image")
        assert image_block["source"]["type"] == "base64"
        assert image_block["source"]["media_type"] == "image/jpeg"
        assert image_block["source"]["data"] == "/9j/abc123"

    @pytest.mark.asyncio
    async def test_base64_data_preserved_exactly(self):
        """Base64 payload is passed through unmodified."""
        from services.claude_proxy import _translate_image_block

        b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        block = {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        }
        result = _translate_image_block(block)
        assert result["source"]["data"] == b64

    @pytest.mark.asyncio
    async def test_non_image_blocks_pass_through(self):
        """Text blocks are left unchanged by translation."""
        from services.claude_proxy import _translate_image_block

        text_block = {"type": "text", "text": "hello"}
        assert _translate_image_block(text_block) == text_block

    @pytest.mark.asyncio
    async def test_media_type_extracted_from_data_uri(self):
        """media_type is correctly extracted from data URI."""
        from services.claude_proxy import _translate_image_block

        block = {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,abc"},
        }
        result = _translate_image_block(block)
        assert result["source"]["media_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_url_image_passes_through_as_url_source(self):
        """HTTPS image URLs become source.type=url."""
        from services.claude_proxy import _translate_image_block

        block = {
            "type": "image_url",
            "image_url": {"url": "https://example.com/img.jpg"},
        }
        result = _translate_image_block(block)
        assert result["source"]["type"] == "url"
        assert result["source"]["url"] == "https://example.com/img.jpg"


# ---------------------------------------------------------------------------
# TestCompleteStructuredOutput
# ---------------------------------------------------------------------------

class TestCompleteStructuredOutput:
    """Verify --json-schema flag and structured_output extraction."""

    @pytest.mark.asyncio
    async def test_json_schema_flag_passed_to_cli(self):
        """--json-schema arg is included when response_format.type == json_schema."""
        from services.claude_proxy import app

        schema = {"name": "MySchema", "schema": {"type": "object", "properties": {}}}
        proc = _make_mock_proc()
        with _patch_proc(proc) as mock_exec, _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "go"}],
                        "response_format": {"type": "json_schema", "json_schema": schema},
                    },
                )

        call_args = list(mock_exec.call_args[0])
        assert "--json-schema" in call_args

    @pytest.mark.asyncio
    async def test_structured_output_returned_as_content(self):
        """structured_output from CLI result is JSON-encoded into response content."""
        from services.claude_proxy import app

        struct_result = (
            b'{"type":"result","subtype":"success","is_error":false,'
            b'"result":"ignored","structured_output":{"answer":42},'
            b'"usage":{"input_tokens":5,"output_tokens":5},'
            b'"stop_reason":"end_turn"}\n'
        )
        schema = {"name": "MySchema", "schema": {"type": "object"}}
        proc = _make_mock_proc(stdout=struct_result)
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "compute"}],
                        "response_format": {"type": "json_schema", "json_schema": schema},
                    },
                )

        body = resp.json()
        assert resp.status_code == 200
        content = body["choices"][0]["message"]["content"]
        assert json.loads(content) == {"answer": 42}

    @pytest.mark.asyncio
    async def test_no_json_schema_flag_for_text_format(self):
        """--json-schema must NOT be added when response_format is absent."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc) as mock_exec, _patch_config():
            async with _make_client(app) as client:
                await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )

        call_args = list(mock_exec.call_args[0])
        assert "--json-schema" not in call_args


# ---------------------------------------------------------------------------
# TestCompleteErrorHandling
# ---------------------------------------------------------------------------

class TestCompleteErrorHandling:
    """Error taxonomy: timeout → 504, nonzero → 502, malformed → 502, disallowed → 422."""

    @pytest.mark.asyncio
    async def test_timeout_returns_504(self):
        """asyncio.TimeoutError from CLI produces 504."""
        from services.claude_proxy import app

        async def _timeout_proc(*args, **kwargs):
            proc = MagicMock()
            proc.returncode = None
            proc.kill = MagicMock()
            proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
            return proc

        with patch("asyncio.create_subprocess_exec", new=_timeout_proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "wait"}],
                    },
                )

        assert resp.status_code == 504

    @pytest.mark.asyncio
    async def test_nonzero_exit_returns_502(self):
        """Non-zero exit code produces 502 without leaking stderr."""
        from services.claude_proxy import app

        proc = _make_mock_proc(stdout=b"", returncode=1)
        proc.communicate = AsyncMock(return_value=(b"", b"internal secret error"))
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "boom"}],
                    },
                )

        assert resp.status_code == 502
        # stderr must not leak
        assert "internal secret error" not in resp.text

    @pytest.mark.asyncio
    async def test_malformed_stdout_returns_502(self):
        """Unparseable stdout (no result line) produces 502."""
        from services.claude_proxy import app

        proc = _make_mock_proc(stdout=b"not json\n{\"type\":\"other\"}\n")
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "parse me"}],
                    },
                )

        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_is_error_true_returns_502(self):
        """result with is_error=true produces 502."""
        from services.claude_proxy import app

        err_result = (
            b'{"type":"result","subtype":"error","is_error":true,'
            b'"result":"something went wrong","usage":{}}\n'
        )
        proc = _make_mock_proc(stdout=err_result)
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "claude-sonnet-4-6",
                        "messages": [{"role": "user", "content": "err"}],
                    },
                )

        assert resp.status_code == 502

    @pytest.mark.asyncio
    async def test_disallowed_model_returns_422(self):
        """Model not in allowlist produces 422."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc), _patch_config():
            async with _make_client(app) as client:
                resp = await client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )

        assert resp.status_code == 422
