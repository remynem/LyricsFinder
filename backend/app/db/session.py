import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# Strip sslmode/ssl/channel_binding params — asyncpg requires ssl via connect_args, not URL params
_url = settings.DATABASE_URL
for _p in ("sslmode=require", "sslmode=disable", "ssl=require", "ssl=disable",
           "channel_binding=require", "channel_binding=disable"):
    _url = _url.replace(f"?{_p}", "").replace(f"&{_p}", "")

# Auto-detect if SSL is needed (Neon, AWS RDS, Supabase)
_needs_ssl = any(h in _url for h in ("neon.tech", "amazonaws.com", "supabase.co"))
_connect_args = {"ssl": ssl.create_default_context()} if _needs_ssl else {}

engine = create_async_engine(
    _url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
