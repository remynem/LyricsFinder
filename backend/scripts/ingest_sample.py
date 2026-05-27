#!/usr/bin/env python3
"""
Ingest a sample corpus of ~1 000 songs for local development and testing.

Uses public-domain or Creative Commons song data. Does NOT include
full commercial lyrics — uses placeholder verses for search testing.

Usage:
    docker compose exec backend python scripts/ingest_sample.py
    # or locally:
    python scripts/ingest_sample.py
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

import httpx

# ─── Sample data (public domain / CC / placeholder) ──────────────────────────

SONGS = [
    {
        "track_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "hardy-temps-amour")),
        "title": "Le Temps de l'Amour",
        "artist": "Françoise Hardy",
        "album": "Tous les garçons et les filles",
        "release_year": 1963,
        "language": "fr",
        "lyrics": (
            "Le temps de l'amour\n"
            "C'est long et c'est court\n"
            "Ça dure toujours\n"
            "Comme un petit cœur qui bat\n"
            "Comme un petit cœur qui bat\n"
            "Tu t'en vas déjà\n"
            "Mais tu reviendras\n"
            "Il n'y a que ça\n"
            "Le temps de l'amour"
        ),
        "external_ids": {"spotify_id": "3n3Ppam7vgaVa1iaRUIOKE"},
    },
    {
        "track_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "oz-rainbow")),
        "title": "Over the Rainbow",
        "artist": "Judy Garland",
        "album": "The Wizard of Oz (Soundtrack)",
        "release_year": 1939,
        "language": "en",
        "lyrics": (
            "Somewhere over the rainbow\n"
            "Way up high\n"
            "There's a land that I heard of\n"
            "Once in a lullaby\n"
            "Somewhere over the rainbow\n"
            "Skies are blue\n"
            "And the dreams that you dare to dream\n"
            "Really do come true"
        ),
        "external_ids": {},
    },
    {
        "track_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "beethoven-ode")),
        "title": "Ode to Joy (text)",
        "artist": "Friedrich Schiller / Beethoven",
        "album": "Symphony No. 9",
        "release_year": 1824,
        "language": "de",
        "lyrics": (
            "Freude, schöner Götterfunken\n"
            "Tochter aus Elysium\n"
            "Wir betreten feuertrunken\n"
            "Himmlische, dein Heiligtum\n"
            "Deine Zauber binden wieder\n"
            "Was die Mode streng geteilt\n"
            "Alle Menschen werden Brüder\n"
            "Wo dein sanfter Flügel weilt"
        ),
        "external_ids": {},
    },
]

# Generate additional placeholder songs to reach ~1 000
def generate_songs(base_count: int = 1000) -> list[dict]:
    languages = ["en", "fr", "es", "de", "it", "pt", "ar", "ja", "ko"]
    artists = [
        "Test Artist A", "Test Artist B", "Test Artist C",
        "Sample Band", "Demo Singer", "Placeholder Group",
    ]
    base = SONGS.copy()
    for i in range(base_count - len(SONGS)):
        lang = languages[i % len(languages)]
        artist = artists[i % len(artists)]
        base.append({
            "track_id": str(uuid.uuid4()),
            "title": f"Sample Song {i+1}",
            "artist": artist,
            "album": f"Album {i // 10 + 1}",
            "release_year": 1960 + (i % 65),
            "language": lang,
            "lyrics": (
                f"Verse one of sample song {i+1}\n"
                f"With meaningful words and rhyme\n"
                f"This is a test lyric fragment {i+1}\n"
                f"For searching and indexing in time\n"
                f"\n"
                f"Chorus of sample song {i+1}\n"
                f"La la la, test phrase here\n"
                f"Another line to index and find\n"
                f"Making the search engine clear"
            ),
            "external_ids": {},
        })
    return base


async def ingest(songs: list[dict], api_url: str, api_key: str):
    batch_size = 100
    total_ok = 0
    total_segs = 0

    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(songs), batch_size):
            batch = songs[i : i + batch_size]
            print(f"  Ingesting songs {i+1}–{i+len(batch)}…", end=" ", flush=True)
            try:
                resp = await client.post(
                    f"{api_url}/ingest",
                    json={"songs": batch},
                    headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                )
                resp.raise_for_status()
                result = resp.json()
                total_ok += result["songs_ingested"]
                total_segs += result["segments_created"]
                print(f"✓ {result['songs_ingested']} songs, {result['segments_created']} segments ({result['duration_seconds']:.1f}s)")
            except Exception as exc:
                print(f"✗ Error: {exc}")

    print(f"\nDone: {total_ok} songs, {total_segs} segments ingested.")


if __name__ == "__main__":
    import os
    api_url = os.getenv("API_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "dev-key")

    songs = generate_songs(1000)
    print(f"Ingesting {len(songs)} songs to {api_url}…\n")
    asyncio.run(ingest(songs, api_url, api_key))
