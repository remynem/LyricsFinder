from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.db.session import get_db
from app.db.repos.song import get_song
from app.services.spotify import get_spotify_preview

router = APIRouter()


class AudioPreview(BaseModel):
    spotify_preview_url: Optional[str]
    spotify_track_url: Optional[str]


class TrackResponse(BaseModel):
    track_id: str
    title: str
    artist: str
    album: Optional[str]
    release_year: Optional[int]
    language: Optional[str]
    lyrics_excerpt: str
    full_lyrics_available: bool
    audio_preview: Optional[AudioPreview]
    external_links: dict


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(track_id: str, _: str = Depends(verify_api_key), db=Depends(get_db)):
    song = await get_song(db, track_id)
    if not song:
        raise HTTPException(status_code=404, detail="Track not found")

    lines = (song.lyrics or "").splitlines()
    excerpt = "\n".join(lines[:4])  # Max 4 lines — licence compliance

    preview = None
    if song.spotify_id:
        preview = await get_spotify_preview(song.title, song.artist, song.spotify_id)

    return TrackResponse(
        track_id=song.track_id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        release_year=song.release_year,
        language=song.language,
        lyrics_excerpt=excerpt,
        full_lyrics_available=False,
        audio_preview=AudioPreview(**preview) if preview else None,
        external_links={"spotify": f"https://open.spotify.com/track/{song.spotify_id}" if song.spotify_id else None},
    )
