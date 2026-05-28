import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

H = {"X-API-Key": settings.API_KEY, "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_search_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/search", json={"query_text": "test"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/search", json={"query_text": ""}, headers=H)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_search_valid_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/search", json={"query_text": "comme un petit coeur", "top_k": 3}, headers=H)
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert "query_id" in body
    assert "latency_ms" in body


@pytest.mark.asyncio
async def test_injection_safe():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/search", json={"query_text": '"; DROP INDEX lyrics; --'}, headers=H)
    assert r.status_code in (200, 422)
