from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import DB_URL

engine = create_async_engine(DB_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with SessionLocal() as session:
        yield session
