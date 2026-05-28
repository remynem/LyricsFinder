#!/usr/bin/env python3
"""Ingest 1000 sample songs. Usage: python scripts/ingest_sample.py"""
import asyncio, os, uuid, httpx

BASE_SONGS = [
    {"track_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "hardy")),
     "title": "Le Temps de l'Amour", "artist": "Françoise Hardy",
     "album": "Tous les garçons et les filles", "release_year": 1963, "language": "fr",
     "lyrics": "Le temps de l'amour\nC'est long et c'est court\nÇa dure toujours\nComme un petit cœur qui bat\nTu t'en vas déjà\nMais tu reviendras",
     "external_ids": {"spotify_id": "3n3Ppam7vgaVa1iaRUIOKE"}},
    {"track_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "rainbow")),
     "title": "Over the Rainbow", "artist": "Judy Garland",
     "album": "The Wizard of Oz", "release_year": 1939, "language": "en",
     "lyrics": "Somewhere over the rainbow\nWay up high\nThere's a land that I heard of\nOnce in a lullaby",
     "external_ids": {}},
]


def generate(count=1000):
    langs = ["en", "fr", "es", "de", "it", "pt", "ar"]
    songs = BASE_SONGS.copy()
    for i in range(count - len(BASE_SONGS)):
        songs.append({
            "track_id": str(uuid.uuid4()),
            "title": f"Sample Song {i + 1}",
            "artist": f"Artist {i % 10 + 1}",
            "album": f"Album {i // 10 + 1}",
            "release_year": 1960 + (i % 65),
            "language": langs[i % len(langs)],
            "lyrics": f"Verse one of song {i + 1}\nWith meaningful words and rhyme\nTest lyric fragment {i + 1}\nFor searching in time\n\nChorus la la la\nAnother line to find",
            "external_ids": {},
        })
    return songs


async def run(songs, api_url, api_key):
    total_ok = total_segs = 0
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(songs), 100):
            batch = songs[i:i + 100]
            print(f"  Batch {i // 100 + 1}...", end=" ", flush=True)
            try:
                r = await client.post(f"{api_url}/ingest", json={"songs": batch},
                                      headers={"X-API-Key": api_key, "Content-Type": "application/json"})
                r.raise_for_status()
                d = r.json()
                total_ok += d["songs_ingested"]
                total_segs += d["segments_created"]
                print(f"✓ {d['songs_ingested']} songs, {d['segments_created']} segments")
            except Exception as e:
                print(f"✗ {e}")
    print(f"\n✓ Total: {total_ok} songs, {total_segs} segments")


if __name__ == "__main__":
    songs = generate(1000)
    print(f"Ingesting {len(songs)} songs...\n")
    asyncio.run(run(songs, os.getenv("API_URL", "http://localhost:8000"), os.getenv("API_KEY", "dev-key")))
