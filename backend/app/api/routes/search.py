"""POST /search — hybrid semantic + lexical search with cross-encoder reranking."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.auth import verify_api_key
from app.services.language import detect_language
from app.services.embeddings import get_embedder
from app.services.vector_db import get_vector_db
from app.services.lexical import get_lexical_search
from app.services.reranker import get_reranker
from app.services.spotify import get_spotify_preview
from app.services.cache import get_cache
from app.db.session import get_db
from app.models.query_log import QueryLog

router = APIRouter()


class SearchRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(10, ge=1, le=50)
    language_hint: Optional[str] = None
    use_translation: bool = False
    filter_year_min: Optional[int] = None
    filter_year_max: Optional[int] = None
    filter_language: Optional[str] = None


class AudioPreview(BaseModel):
    spotify_preview_url: Optional[str]
    spotify_track_url: Optional[str]


class BestSegment(BaseModel):
    text: str
    line_offset: int
    context: str


class SearchResult(BaseModel):
    track_id: str
    title: str
    artist: str
    album: Optional[str]
    release_year: Optional[int]
    language: Optional[str]
    confidence_score: float
    best_segment: BestSegment
    audio_preview: Optional[AudioPreview]


class SearchResponse(BaseModel):
    query_id: str
    detected_language: str
    results: list[SearchResult]
    total: int
    latency_ms: int


@router.post("", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    _: str = Depends(verify_api_key),
    db=Depends(get_db),
):
    t0 = time.monotonic()
    query_id = str(uuid.uuid4())

    # Sanitize input
    query_text = req.query_text.strip()

    # Check cache
    cache = get_cache()
    cache_key = f"search:{hash(query_text)}:{req.top_k}:{req.filter_language}"
    cached = await cache.get(cache_key)
    if cached:
        return SearchResponse(**cached)

    # 1. Language detection
    detected_lang = req.language_hint or detect_language(query_text)

    # 2. Generate query embedding
    embedder = get_embedder()
    queries_to_embed = [query_text]

    if req.use_translation and detected_lang != "en":
        from app.services.translation import translate
        translated = await translate(query_text, target_lang="en")
        if translated:
            queries_to_embed.append(translated)

    embeddings = await embedder.embed_batch(queries_to_embed)

    # 3. ANN search in vector DB
    vector_db = get_vector_db()
    vector_candidates = []
    for embedding in embeddings:
        hits = await vector_db.search(
            embedding=embedding,
            limit=settings.SEARCH_CANDIDATE_LIMIT,
            filter_language=req.filter_language,
            filter_year_min=req.filter_year_min,
            filter_year_max=req.filter_year_max,
        )
        vector_candidates.extend(hits)

    # 4. BM25 lexical search
    lexical = get_lexical_search()
    lexical_candidates = await lexical.search(
        query=query_text,
        limit=min(settings.SEARCH_CANDIDATE_LIMIT // 2, 100),
        filter_language=req.filter_language,
    )

    # 5. Hybrid merge (Reciprocal Rank Fusion)
    merged = _reciprocal_rank_fusion(vector_candidates, lexical_candidates)
    top_candidates = merged[:settings.SEARCH_CANDIDATE_LIMIT]

    # 6. Cross-encoder reranking
    reranker = get_reranker()
    reranked = await reranker.rerank(
        query=query_text,
        candidates=top_candidates,
        batch_size=settings.RERANKER_BATCH_SIZE,
    )

    # 7. Aggregate by track (best segment per track)
    tracks: dict[str, dict] = {}
    for segment in reranked:
        tid = segment["track_id"]
        if tid not in tracks or segment["score"] > tracks[tid]["score"]:
            tracks[tid] = segment

    # Sort by score, take top_k
    sorted_tracks = sorted(tracks.values(), key=lambda x: x["score"], reverse=True)[:req.top_k]

    # 8. Enrich with Spotify preview
    results = []
    for track in sorted_tracks:
        preview = None
        if settings.SPOTIFY_CLIENT_ID:
            preview = await get_spotify_preview(
                title=track["title"],
                artist=track["artist"],
                spotify_id=track.get("spotify_id"),
            )

        results.append(SearchResult(
            track_id=track["track_id"],
            title=track["title"],
            artist=track["artist"],
            album=track.get("album"),
            release_year=track.get("release_year"),
            language=track.get("language"),
            confidence_score=round(track["score"], 4),
            best_segment=BestSegment(
                text=track["segment_text"],
                line_offset=track["line_offset"],
                context=track["context"],
            ),
            audio_preview=preview,
        ))

    latency_ms = int((time.monotonic() - t0) * 1000)

    response = SearchResponse(
        query_id=query_id,
        detected_language=detected_lang,
        results=results,
        total=len(results),
        latency_ms=latency_ms,
    )

    # Log query
    await _log_query(db, query_id, query_text, detected_lang, results, latency_ms)

    # Cache
    await cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL_SECONDS)

    return response


def _reciprocal_rank_fusion(list_a: list, list_b: list, k: int = 60) -> list:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, doc in enumerate(list_a):
        seg_id = doc["segment_id"]
        scores[seg_id] = scores.get(seg_id, 0) + 1 / (k + rank + 1)
        docs[seg_id] = doc

    for rank, doc in enumerate(list_b):
        seg_id = doc["segment_id"]
        scores[seg_id] = scores.get(seg_id, 0) + 1 / (k + rank + 1)
        docs.setdefault(seg_id, doc)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for seg_id, score in ranked:
        doc = docs[seg_id].copy()
        doc["rrf_score"] = score
        result.append(doc)
    return result


async def _log_query(db, query_id, query_text, lang, results, latency_ms):
    try:
        top_track_id = results[0].track_id if results else None
        log = QueryLog(
            query_id=query_id,
            query_text=query_text[:500],
            detected_language=lang,
            top_result_track_id=top_track_id,
            result_count=len(results),
            latency_ms=latency_ms,
        )
        db.add(log)
        await db.commit()
    except Exception:
        pass
