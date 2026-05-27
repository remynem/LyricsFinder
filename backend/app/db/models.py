from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Song(Base):
    __tablename__ = "songs"
    track_id      = Column(String, primary_key=True)
    title         = Column(String, nullable=False)
    artist        = Column(String, nullable=False)
    album         = Column(String)
    release_year  = Column(Integer)
    language      = Column(String(10))
    lyrics        = Column(Text)
    spotify_id    = Column(String)
    musixmatch_id = Column(String)
    created_at    = Column(DateTime, default=datetime.utcnow)


class LyricSegment(Base):
    __tablename__ = "lyric_segments"
    segment_id  = Column(String, primary_key=True)
    track_id    = Column(String, nullable=False, index=True)
    text        = Column(Text, nullable=False)
    line_offset = Column(Integer, default=0)
    context     = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)


class QueryLog(Base):
    __tablename__ = "query_logs"
    id                  = Column(String, primary_key=True)
    query_id            = Column(String, unique=True, index=True)
    query_text          = Column(String(500))
    detected_language   = Column(String(10))
    top_result_track_id = Column(String)
    result_count        = Column(Integer)
    latency_ms          = Column(Integer)
    created_at          = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id               = Column(String, primary_key=True)
    query_id         = Column(String, index=True)
    track_id         = Column(String)
    is_correct       = Column(Boolean)
    clicked_position = Column(Integer)
    created_at       = Column(DateTime, default=datetime.utcnow)
