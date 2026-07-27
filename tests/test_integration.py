"""tests/test_integration.py — Integration tests (requires running app)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestLiveness:
    @pytest.mark.asyncio
    async def test_returns_200(self, client: AsyncClient) -> None:
        assert (await client.get("/api/v1/health/live")).status_code == 200

    @pytest.mark.asyncio
    async def test_response_shape(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/health/live")).json()
        assert data["status"] == "alive"
        assert "service" in data and "version" in data

    @pytest.mark.asyncio
    async def test_never_returns_503(self, client: AsyncClient) -> None:
        assert (await client.get("/api/v1/health/live")).status_code != 503


class TestReadiness:
    @pytest.mark.asyncio
    async def test_returns_200_or_503(self, client: AsyncClient) -> None:
        assert (await client.get("/api/v1/health/ready")).status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_has_checks(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/health/ready")).json()
        assert "checks" in data and "postgres" in data["checks"]


class TestRequestTracing:
    @pytest.mark.asyncio
    async def test_request_id_in_response(self, client: AsyncClient) -> None:
        assert "x-request-id" in (await client.get("/api/v1/health/live")).headers

    @pytest.mark.asyncio
    async def test_client_request_id_echoed(self, client: AsyncClient) -> None:
        my_id = "trace-id-12345"
        resp = await client.get("/api/v1/health/live", headers={"X-Request-ID": my_id})
        assert resp.headers["x-request-id"] == my_id


class TestErrors:
    @pytest.mark.asyncio
    async def test_404_for_unknown_route(self, client: AsyncClient) -> None:
        assert (await client.get("/api/v1/doesnt-exist")).status_code == 404

    @pytest.mark.asyncio
    async def test_error_envelope_shape(self, client: AsyncClient) -> None:
        data = (await client.get("/api/v1/doesnt-exist")).json()
        assert "error" in data
        assert all(k in data["error"] for k in ("code", "message", "request_id"))
