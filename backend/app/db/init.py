"""Run with: python -m app.db.init"""
import asyncio
from app.db.session import engine
from app.db.models import Base


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created successfully")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
