import logging
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

logger = logging.getLogger(__name__)
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

    logger.info(f"Ingest started: {len(req.songs)} songs")

    # Step 1 — get services
    try:
        embedder = get_embedder()
        logger.info(f"Embedder: {type(embedder).__name__}")
    except Exception as e:
        return IngestResponse(songs_ingested=0, segments_created=0, embeddings_generated=0,
                              duration_seconds=0, errors=[f"Embedder init failed: {e}"])

    try:
        vector_db = get_vector_db()
        logger.info(f"VectorDB: {type(vector_db).__name__}")
    except Exception as e:
        return IngestResponse(songs_ingested=0, segments_created=0, embeddings_generated=0,
                              duration_seconds=0, errors=[f"VectorDB init failed: {e}"])

    try:
        lexical = get_lexical_search()
        logger.info(f"Lexical: {type(lexical).__name__}")
    except Exception as e:
        logger.warning(f"Lexical init failed (non-fatal): {e}")
        from app.services.lexical import NoopLexicalSearch
        lexical = NoopLexicalSearch()

    # Step 2 — process in batches
    for i in range(0, len(req.songs), settings.INGEST_BATCH_SIZE):
        batch = req.songs[i:i + settings.INGEST_BATCH_SIZE]
        logger.info(f"Processing batch {i // settings.INGEST_BATCH_SIZE + 1} ({len(batch)} songs)")

        try:
            # Segment
            all_segments = []
            for song in batch:
                try:
                    segs = deduplicate_segments(segment_lyrics(normalise_text(song.lyrics), song.track_id))
                    for seg in segs:
                        seg.update({
                            "title": song.title,
                            "artist": song.artist,
                            "album": song.album or "",
                            "language": song.language or "",
                            "release_year": song.release_year,
                            "spotify_id": (song.external_ids.spotify_id if song.external_ids else None) or "",
                        })
                    all_segments.extend(segs)
                except Exception as e:
                    logger.error(f"Segment error for {song.track_id}: {e}")
                    errors.append(f"Segment {song.track_id}: {e}")

            logger.info(f"Segments created: {len(all_segments)}")

            if not all_segments:
                logger.warning("No segments generated, skipping batch")
                continue

            # Embed
            try:
                texts = [s["text"] for s in all_segments]
                logger.info(f"Embedding {len(texts)} segments...")
                embeddings = await embedder.embed_batch(texts)
                logger.info(f"Got {len(embeddings)} embeddings, dim={len(embeddings[0]) if embeddings else 0}")
                for seg, emb in zip(all_segments, embeddings):
                    seg["embedding"] = emb
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                errors.append(f"Embedding batch {i // settings.INGEST_BATCH_SIZE}: {e}")
                continue

            # Vector DB upsert
            try:
                logger.info(f"Upserting {len(all_segments)} segments to vector DB...")
                await vector_db.upsert(all_segments)
                logger.info("Vector DB upsert OK")
            except Exception as e:
                logger.error(f"Vector DB upsert error: {e}")
                errors.append(f"VectorDB batch {i // settings.INGEST_BATCH_SIZE}: {e}")
                continue

            # Elasticsearch (non-fatal)
            try:
                await lexical.bulk_index([
                    {"segment_id": s["segment_id"], "track_id": s["track_id"],
                     "text": s["text"], "title": s.get("title", ""),
                     "artist": s.get("artist", ""), "language": s.get("language", ""),
                     "release_year": s.get("release_year")}
                    for s in all_segments
                ])
            except Exception as e:
                logger.warning(f"ES index failed (non-fatal): {e}")

            # PostgreSQL
            try:
                logger.info("Saving to PostgreSQL...")
                for song in batch:
                    await create_song(db, song)
                    await create_segments(db, [s for s in all_segments if s["track_id"] == song.track_id])
                await db.commit()
                logger.info("PostgreSQL commit OK")
            except Exception as e:
                logger.error(f"PostgreSQL error: {e}")
                errors.append(f"DB batch {i // settings.INGEST_BATCH_SIZE}: {e}")
                # Don't continue — segments are already in vector DB
                await db.rollback()

            total_segments += len(all_segments)
            songs_ok += len(batch)
            logger.info(f"Batch OK: {len(batch)} songs, {len(all_segments)} segments")

        except Exception as exc:
            msg = f"Batch {i // settings.INGEST_BATCH_SIZE}: {str(exc)}"
            logger.error(msg)
            errors.append(msg)

    duration = round(time.monotonic() - t0, 2)
    logger.info(f"Ingest done: {songs_ok} songs, {total_segments} segments, {duration}s, errors={errors}")

    return IngestResponse(
        songs_ingested=songs_ok,
        segments_created=total_segments,
        embeddings_generated=total_segments,
        duration_seconds=duration,
        errors=errors,
    )
