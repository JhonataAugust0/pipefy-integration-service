import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL: str = os.environ["DATABASE_URL"]

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

class Base(DeclarativeBase):
    """
    Base declarativa compartilhada por todos os modelos SQLAlchemy.
    Importada pelo env.py do Alembic para autogenerate de migrations.
    """

    pass


AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db() -> AsyncSession:
    """
    Dependency FastAPI. Gerencia ciclo de vida da sessão por request:
    abre, injeta na rota, faz commit ou rollback e fecha.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
