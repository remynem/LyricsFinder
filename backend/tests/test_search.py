"""Integration tests for POST /search."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings


@pytest.fixture
def api_headers():
    return {"X-API-Key": settings.API_KEY, "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_search_returns_results(api_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/search",
            json={"query_text": "comme un petit coeur qui bat", "top_k": 5},
            headers=api_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert "query_id" in body
    assert "detected_language" in body
    assert "latency_ms" in body
    assert body["detected_language"] == "fr"


@pytest.mark.asyncio
async def test_search_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/search",
            json={"query_text": "test"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query_rejected(api_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/search",
            json={"query_text": ""},
            headers=api_headers,
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_with_filters(api_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/search",
            json={
                "query_text": "love",
                "top_k": 3,
                "filter_language": "en",
                "filter_year_min": 2000,
                "filter_year_max": 2010,
            },
            headers=api_headers,
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_injection_sanitised(api_headers):
    """Elasticsearch injection attempt should be safely handled."""
    malicious = '"; DROP INDEX lyrics; --'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/search",
            json={"query_text": malicious, "top_k": 3},
            headers=api_headers,
        )
    # Should not raise 500
    assert response.status_code in (200, 422)


@pytest.mark.asyncio
async def test_search_result_schema(api_headers, sample_song_in_db):
    """If corpus has been seeded, top result must match expected schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/search",
            json={"query_text": "comme un petit coeur", "top_k": 1},
            headers=api_headers,
        )
    body = response.json()
    if body["total"] > 0:
        result = body["results"][0]
        assert "track_id" in result
        assert "title" in result
        assert "artist" in result
        assert "confidence_score" in result
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert "best_segment" in result
        assert "text" in result["best_segment"]
