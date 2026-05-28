import time
import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.auth import verify_api_key
from app.core.config import settings
from app.services.language import detect_language
from app.services.embeddings import get_embedder
from app.services.vector_db import get_vector_db
from app.services.lexical import get_lexical_search
from app.services.reranker import get_reranker
from app.services.spotify import get_spotify_preview
from app.services.cache import get_cache
from app.db.session import get_db
from app.db.models import QueryLog

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
async def search(req: SearchRequest, _: str = Depends(verify_api_key), db=Depends(get_db)):
    t0 = time.monotonic()
    query_id = str(uuid.uuid4())
    query_text = req.query_text.strip()

    cache = get_cache()
    cached = await cache.get(f"search:{hash(query_text)}:{req.top_k}:{req.filter_language}")
    if cached:
        return SearchResponse(**cached)

    detected_lang = req.language_hint or detect_language(query_text)
    queries = [query_text]
    if req.use_translation and detected_lang != "en":
        from app.services.translation import translate
        translated = await translate(query_text)
        if translated:
            queries.append(translated)

    embeddings = await get_embedder().embed_batch(queries)
    vector_candidates = []
    for emb in embeddings:
        hits = await get_vector_db().search(
            embedding=emb, limit=settings.SEARCH_CANDIDATE_LIMIT,
            filter_language=req.filter_language,
            filter_year_min=req.filter_year_min, filter_year_max=req.filter_year_max)
        vector_candidates.extend(hits)

    lexical_candidates = await get_lexical_search().search(query_text, limit=50, filter_language=req.filter_language)
    merged = _rrf(vector_candidates, lexical_candidates)[:settings.SEARCH_CANDIDATE_LIMIT]
    reranked = await get_reranker().rerank(query_text, merged, settings.RERANKER_BATCH_SIZE)

    tracks: dict[str, dict] = {}
    for seg in reranked:
        tid = seg["track_id"]
        if tid not in tracks or seg["score"] > tracks[tid]["score"]:
            tracks[tid] = seg

    results = []
    for track in sorted(tracks.values(), key=lambda x: x["score"], reverse=True)[:req.top_k]:
        preview = None
        if settings.SPOTIFY_CLIENT_ID:
            preview = await get_spotify_preview(track.get("title", ""), track.get("artist", ""), track.get("spotify_id"))
        results.append(SearchResult(
            track_id=track["track_id"], title=track.get("title", ""), artist=track.get("artist", ""),
            album=track.get("album"), release_year=track.get("release_year"), language=track.get("language"),
            confidence_score=round(min(max(float(track["score"]), 0.0), 1.0), 4),
            best_segment=BestSegment(text=track["text"], line_offset=track.get("line_offset", 0),
                                     context=track.get("context", "")),
            audio_preview=AudioPreview(**preview) if preview else None,
        ))

    latency_ms = int((time.monotonic() - t0) * 1000)
    response = SearchResponse(query_id=query_id, detected_language=detected_lang,
                               results=results, total=len(results), latency_ms=latency_ms)

    try:
        db.add(QueryLog(id=str(uuid.uuid4()), query_id=query_id, query_text=query_text[:500],
                        detected_language=detected_lang,
                        top_result_track_id=results[0].track_id if results else None,
                        result_count=len(results), latency_ms=latency_ms))
        await db.commit()
    except Exception:
        pass

    await cache.set(f"search:{hash(query_text)}:{req.top_k}:{req.filter_language}",
                    response.model_dump(), ttl=settings.CACHE_TTL_SECONDS)
    return response


def _rrf(a: list, b: list, k: int = 60) -> list:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for rank, doc in enumerate(a):
        sid = doc.get("segment_id", str(rank))
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank + 1)
        docs[sid] = doc
    for rank, doc in enumerate(b):
        sid = doc.get("segment_id", str(rank))
        scores[sid] = scores.get(sid, 0) + 1 / (k + rank + 1)
        docs.setdefault(sid, doc)
    result = []
    for sid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        d = docs[sid].copy()
        d["score"] = score
        result.append(d)
    return result
