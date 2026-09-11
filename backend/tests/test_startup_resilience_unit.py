from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

import server


from starlette.testclient import TestClient

import server


def test_startup_indexing_resilience_on_database_timeout():
    """Verify that if database index creation fails or times out, on_startup does not crash."""
    async def _run():
        with patch.object(server, "_ensure_indexes", new=AsyncMock(side_effect=asyncio.TimeoutError("DB slow"))):
            # Should complete cleanly without raising exception
            await server.on_startup(process_role="api", allow_loop_schedule=False)

    asyncio.run(_run())


def test_root_and_health_endpoints_respond():
    """Verify that root / and /health and /api/health routes respond properly."""
    client = TestClient(server.app)

    # Root endpoint
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json().get("service") == "dog-trainers-directory-match-engine"

    # Health endpoint at root
    health_resp = client.get("/health")
    assert health_resp.status_code in (200, 503)
    assert "service" in health_resp.json()

    # Health endpoint at /api/health
    api_health_resp = client.get("/api/health")
    assert api_health_resp.status_code in (200, 503)
    assert "service" in api_health_resp.json()


def test_cors_headers_match_configured_origins():
    """Verify that requests from allowed origins receive proper Access-Control-Allow-Origin header."""
    client = TestClient(server.app)
    headers = {
        "Origin": "https://gen-lang-client-0028123502.web.app",
        "Access-Control-Request-Method": "GET",
    }
    # Preflight OPTIONS request
    resp = client.options("/api/config", headers=headers)
    assert resp.headers.get("access-control-allow-origin") == "https://gen-lang-client-0028123502.web.app"

