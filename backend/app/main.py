"""LyricFinder FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ingest, search, track, feedback, health
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import engine
from app.db import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Startup: create tables, warm up connections
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    # Shutdown: close connections
    await engine.dispose()


app = FastAPI(
    title="LyricFinder API",
    version="0.1.0",
    description="Search any song from a lyric fragment — multilingual, fuzzy, semantic.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(track.router, prefix="/track", tags=["track"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
