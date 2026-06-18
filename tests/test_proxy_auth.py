"""
Authentication tests for the Claude Code Proxy v2.

Covers: valid token, missing token, wrong token, empty token, /health bypass.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

VALID_TOKEN = "test-secret-token"

MOCK_RESULT = (
    b'{"type":"result","subtype":"success","is_error":false,'
    b'"result":"ok","usage":{"input_tokens":1,"output_tokens":1},'
    b'"stop_reason":"end_turn"}\n'
)

_COMPLETIONS_PAYLOAD = {
    "model": "claude-sonnet-4-6",
    "messages": [{"role": "user", "content": "hello"}],
}


def _make_mock_proc(stdout: bytes = MOCK_RESULT) -> MagicMock:
    proc = MagicMock()
    proc.returncode = 0
    proc.kill = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    return proc


def _patch_proc(proc: MagicMock):
    return patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    )


def _patch_config(**overrides):
    defaults = {
        "MCP_PROXY_AUTH_TOKEN": VALID_TOKEN,
        "CLAUDE_PROXY_MAX_CONCURRENCY": 4,
        "CLAUDE_PROXY_TIMEOUT": 300,
        "CLAUDE_PROXY_MODEL_ALLOWLIST": "claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-6",
    }
    defaults.update(overrides)
    return patch.multiple("services.claude_proxy.Config", **defaults)


# ---------------------------------------------------------------------------
# TestAuthPositive
# ---------------------------------------------------------------------------

class TestAuthPositive:
    @pytest.mark.asyncio
    async def test_valid_bearer_token_accepted(self):
        """Correct Bearer token receives 200."""
        from services.claude_proxy import app

        proc = _make_mock_proc()
        with _patch_proc(proc), _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": f"Bearer {VALID_TOKEN}"},
            ) as client:
                resp = await client.post("/v1/chat/completions", json=_COMPLETIONS_PAYLOAD)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_endpoint_skips_auth(self):
        """GET /health is accessible without any Authorization header."""
        from services.claude_proxy import app

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_health_endpoint_ignores_wrong_token(self):
        """GET /health succeeds even if a wrong token is supplied."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": "Bearer wrong"},
            ) as client:
                resp = await client.get("/health")

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestAuthNegative
# ---------------------------------------------------------------------------

class TestAuthNegative:
    @pytest.mark.asyncio
    async def test_missing_authorization_header_returns_401(self):
        """No Authorization header → 401."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.post("/v1/chat/completions", json=_COMPLETIONS_PAYLOAD)

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_token_returns_401(self):
        """Incorrect Bearer token value → 401."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": "Bearer totally-wrong-token"},
            ) as client:
                resp = await client.post("/v1/chat/completions", json=_COMPLETIONS_PAYLOAD)

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_bearer_token_returns_401(self):
        """Authorization: Bearer <empty> → 401."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": "Bearer "},
            ) as client:
                resp = await client.post("/v1/chat/completions", json=_COMPLETIONS_PAYLOAD)

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_returns_401(self):
        """Authorization: Basic <token> → 401."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": f"Basic {VALID_TOKEN}"},
            ) as client:
                resp = await client.post("/v1/chat/completions", json=_COMPLETIONS_PAYLOAD)

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_models_endpoint_requires_auth(self):
        """GET /v1/models also requires valid Bearer token."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/v1/models")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_models_endpoint_returns_allowlist_with_valid_token(self):
        """GET /v1/models returns all allowed models when authenticated."""
        from services.claude_proxy import app

        with _patch_config():
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                headers={"Authorization": f"Bearer {VALID_TOKEN}"},
            ) as client:
                resp = await client.get("/v1/models")

        assert resp.status_code == 200
        data = resp.json()["data"]
        ids = [m["id"] for m in data]
        assert "claude-sonnet-4-6" in ids
        assert "claude-opus-4-6" in ids
        assert "claude-haiku-4-6" in ids
