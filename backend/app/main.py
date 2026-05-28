from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ingest, search, track, feedback, health
from app.core.config import settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Init DB tables in background — don't block startup if DB is warming up
    try:
        from app.db.session import engine
        from app.db import models
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("✓ Database tables ready")
    except Exception as e:
        logger.warning(f"DB init skipped at startup (will retry on first request): {e}")
    yield


app = FastAPI(
    title="LyricsFinder API",
    version="1.0.0",
    description="Retrouve n'importe quelle chanson depuis un fragment de paroles.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,   tags=["health"])
app.include_router(ingest.router,   prefix="/ingest",   tags=["ingest"])
app.include_router(search.router,   prefix="/search",   tags=["search"])
app.include_router(track.router,    prefix="/track",    tags=["track"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
