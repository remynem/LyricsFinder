from __future__ import annotations
import base64
import time
from typing import Optional
from app.core.config import settings

_token_cache: dict = {}


async def get_spotify_preview(title: str, artist: str, spotify_id: Optional[str] = None) -> Optional[dict]:
    if not settings.SPOTIFY_CLIENT_ID:
        return None
    try:
        token = await _get_token()
        import httpx
        async with httpx.AsyncClient() as client:
            if spotify_id:
                r = await client.get(f"https://api.spotify.com/v1/tracks/{spotify_id}",
                                     headers={"Authorization": f"Bearer {token}"}, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    return {"spotify_preview_url": data.get("preview_url"),
                            "spotify_track_url": data.get("external_urls", {}).get("spotify")}
            r = await client.get("https://api.spotify.com/v1/search",
                                 params={"q": f"{title} {artist}", "type": "track", "limit": 1},
                                 headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                items = r.json().get("tracks", {}).get("items", [])
                if items:
                    return {"spotify_preview_url": items[0].get("preview_url"),
                            "spotify_track_url": items[0].get("external_urls", {}).get("spotify")}
    except Exception:
        pass
    return None


async def _get_token() -> str:
    import httpx
    if _token_cache.get("expires_at", 0) > time.time():
        return _token_cache["token"]
    creds = base64.b64encode(f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        r = await client.post("https://accounts.spotify.com/api/token",
                              data={"grant_type": "client_credentials"},
                              headers={"Authorization": f"Basic {creds}"})
        data = r.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data["expires_in"] - 60
    return _token_cache["token"]
