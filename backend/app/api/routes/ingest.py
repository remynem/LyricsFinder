"""POST /ingest — normalise, segment, embed and index songs."""

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import verify_api_key
from app.core.config import settings
from app.services.text import normalise_text, segment_lyrics, deduplicate_segments
from app.services.embeddings import get_embedder
from app.services.vector_db import get_vector_db
from app.services.lexical import get_lexical_search
from app.db.session import get_db
from app.db.repos.song import create_song, create_segments

router = APIRouter()


class ExternalIds(BaseModel):
    spotify_id: Optional[str] = None
    musixmatch_id: Optional[str] = None
    apple_music_id: Optional[str] = None


class SongInput(BaseModel):
    track_id: str
    title: str
    artist: str
    lyrics: str
    language: Optional[str] = None
    album: Optional[str] = None
    release_year: Optional[int] = None
    external_ids: Optional[ExternalIds] = None


class IngestRequest(BaseModel):
    songs: list[SongInput] = Field(..., min_length=1, max_length=5000)


class IngestResponse(BaseModel):
    songs_ingested: int
    segments_created: int
    embeddings_generated: int
    duration_seconds: float
    errors: list[str] = []


@router.post("", response_model=IngestResponse)
async def ingest(
    req: IngestRequest,
    _: str = Depends(verify_api_key),
    db=Depends(get_db),
):
    t0 = time.monotonic()
    errors = []
    total_segments = 0
    songs_ok = 0

    embedder = get_embedder()
    vector_db = get_vector_db()
    lexical = get_lexical_search()

    # Process in batches
    batch_size = settings.INGEST_BATCH_SIZE

    for i in range(0, len(req.songs), batch_size):
        batch = req.songs[i : i + batch_size]
        try:
            batch_segments, batch_songs_ok = await _process_batch(
                batch, db, embedder, vector_db, lexical
            )
            total_segments += batch_segments
            songs_ok += batch_songs_ok
        except Exception as exc:
            errors.append(f"Batch {i//batch_size}: {str(exc)[:200]}")

    return IngestResponse(
        songs_ingested=songs_ok,
        segments_created=total_segments,
        embeddings_generated=total_segments,
        duration_seconds=round(time.monotonic() - t0, 2),
        errors=errors,
    )


async def _process_batch(batch, db, embedder, vector_db, lexical):
    all_segments = []
    song_records = []

    for song in batch:
        # Normalise text
        normalised = normalise_text(song.lyrics)

        # Segment into 1-3 line chunks
        segments = segment_lyrics(normalised, song.track_id)

        # Deduplicate repeated choruses (keep reference)
        segments = deduplicate_segments(segments)

        all_segments.extend(segments)
        song_records.append(song)

    if not all_segments:
        return 0, 0

    # Batch embed all segments
    texts = [s["text"] for s in all_segments]
    embeddings = await embedder.embed_batch(texts)

    # Attach embeddings to segments
    for seg, emb in zip(all_segments, embeddings):
        seg["embedding"] = emb

    # Upsert to PostgreSQL
    for song in song_records:
        song_segs = [s for s in all_segments if s["track_id"] == song.track_id]
        await create_song(db, song)
        await create_segments(db, song_segs)

    # Upsert to vector DB
    await vector_db.upsert(all_segments)

    # Index in Elasticsearch (full text for BM25)
    docs = [
        {
            "segment_id": s["segment_id"],
            "track_id": s["track_id"],
            "text": s["text"],
            "title": s.get("title", ""),
            "artist": s.get("artist", ""),
            "language": s.get("language", ""),
            "release_year": s.get("release_year"),
        }
        for s in all_segments
    ]
    await lexical.bulk_index(docs)

    await db.commit()
    return len(all_segments), len(song_records)
