import time
from typing import Optional
from fastapi import APIRouter, Depends
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
async def ingest(req: IngestRequest, _: str = Depends(verify_api_key), db=Depends(get_db)):
    t0 = time.monotonic()
    errors, total_segments, songs_ok = [], 0, 0
    embedder = get_embedder()
    vector_db = get_vector_db()
    lexical = get_lexical_search()

    for i in range(0, len(req.songs), settings.INGEST_BATCH_SIZE):
        batch = req.songs[i:i + settings.INGEST_BATCH_SIZE]
        try:
            all_segments = []
            for song in batch:
                segs = deduplicate_segments(segment_lyrics(normalise_text(song.lyrics), song.track_id))
                for seg in segs:
                    seg.update({
                        "title": song.title, "artist": song.artist, "album": song.album or "",
                        "language": song.language or "", "release_year": song.release_year,
                        "spotify_id": (song.external_ids.spotify_id if song.external_ids else None) or "",
                    })
                all_segments.extend(segs)

            if all_segments:
                embeddings = await embedder.embed_batch([s["text"] for s in all_segments])
                for seg, emb in zip(all_segments, embeddings):
                    seg["embedding"] = emb
                await vector_db.upsert(all_segments)
                await lexical.bulk_index([
                    {"segment_id": s["segment_id"], "track_id": s["track_id"], "text": s["text"],
                     "title": s.get("title", ""), "artist": s.get("artist", ""),
                     "language": s.get("language", ""), "release_year": s.get("release_year")}
                    for s in all_segments
                ])

            for song in batch:
                await create_song(db, song)
                await create_segments(db, [s for s in all_segments if s["track_id"] == song.track_id])

            await db.commit()
            total_segments += len(all_segments)
            songs_ok += len(batch)
        except Exception as exc:
            errors.append(f"Batch {i // settings.INGEST_BATCH_SIZE}: {str(exc)[:200]}")

    return IngestResponse(
        songs_ingested=songs_ok, segments_created=total_segments,
        embeddings_generated=total_segments,
        duration_seconds=round(time.monotonic() - t0, 2), errors=errors,
    )
