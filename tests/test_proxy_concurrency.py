"""
Concurrency limiter tests for the Claude Code Proxy v2.

Covers: within-limit requests succeed, exceeding limit returns 429.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


def _patch_config(**overrides):
    defaults = {
        "MCP_PROXY_AUTH_TOKEN": VALID_TOKEN,
        "CLAUDE_PROXY_MAX_CONCURRENCY": 2,
        "CLAUDE_PROXY_TIMEOUT": 300,
        "CLAUDE_PROXY_MODEL_ALLOWLIST": "claude-sonnet-4-6,claude-opus-4-6,claude-haiku-4-6",
    }
    defaults.update(overrides)
    return patch.multiple("services.claude_proxy.Config", **defaults)


def _make_client(app) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )


class TestConcurrencyLimiter:
    async def test_within_limit_requests_succeed(self):
        """A single request completes when concurrency is not exhausted."""
        import services.claude_proxy as proxy_module

        # Reset semaphore so this test uses a fresh one
        proxy_module._semaphore = None

        proc = MagicMock()
        proc.returncode = 0
        proc.kill = MagicMock()
        proc.communicate = AsyncMock(return_value=(MOCK_RESULT, b""))

        with patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)):
            with _patch_config(CLAUDE_PROXY_MAX_CONCURRENCY=2):
                async with _make_client(proxy_module.app) as client:
                    resp = await client.post(
                        "/v1/chat/completions", json=_COMPLETIONS_PAYLOAD
                    )

        assert resp.status_code == 200

    async def test_exceeding_concurrency_returns_429(self):
        """When all semaphore slots are taken, the next request gets 429."""
        import services.claude_proxy as proxy_module

        # Pre-exhaust the semaphore by setting its value to 0 directly
        proxy_module._semaphore = asyncio.Semaphore(0)

        with _patch_config(CLAUDE_PROXY_MAX_CONCURRENCY=0):
            async with _make_client(proxy_module.app) as client:
                resp = await client.post(
                    "/v1/chat/completions", json=_COMPLETIONS_PAYLOAD
                )

        assert resp.status_code == 429

        # Restore for other tests
        proxy_module._semaphore = None

    async def test_concurrent_requests_within_limit_all_succeed(self):
        """Multiple concurrent requests within the limit all complete 200."""
        import services.claude_proxy as proxy_module

        proxy_module._semaphore = None

        async def _slow_proc(*args, **kwargs):
            proc = MagicMock()
            proc.returncode = 0
            proc.kill = MagicMock()
            proc.communicate = AsyncMock(return_value=(MOCK_RESULT, b""))
            return proc

        with patch("asyncio.create_subprocess_exec", new=_slow_proc):
            with _patch_config(CLAUDE_PROXY_MAX_CONCURRENCY=3):
                async with _make_client(proxy_module.app) as client:
                    tasks = [
                        client.post("/v1/chat/completions", json=_COMPLETIONS_PAYLOAD)
                        for _ in range(3)
                    ]
                    responses = await asyncio.gather(*tasks)

        statuses = [r.status_code for r in responses]
        assert all(s == 200 for s in statuses), f"Unexpected statuses: {statuses}"
