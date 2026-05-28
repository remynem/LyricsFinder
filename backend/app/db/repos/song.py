from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Song, LyricSegment


async def create_song(db: AsyncSession, song) -> None:
    external_ids = song.external_ids or {}
    record = Song(
        track_id=song.track_id,
        title=song.title,
        artist=song.artist,
        album=song.album,
        release_year=song.release_year,
        language=song.language,
        lyrics=song.lyrics,
        spotify_id=getattr(external_ids, "spotify_id", None),
        musixmatch_id=getattr(external_ids, "musixmatch_id", None),
    )
    await db.merge(record)


async def create_segments(db: AsyncSession, segments: list[dict]) -> None:
    for seg in segments:
        record = LyricSegment(
            segment_id=seg["segment_id"],
            track_id=seg["track_id"],
            text=seg["text"],
            line_offset=seg.get("line_offset", 0),
            context=seg.get("context", ""),
        )
        await db.merge(record)


async def get_song(db: AsyncSession, track_id: str) -> Song | None:
    result = await db.execute(select(Song).where(Song.track_id == track_id))
    return result.scalar_one_or_none()
