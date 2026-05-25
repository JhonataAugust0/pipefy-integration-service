"""
Infraestrutura de testes

Estratégia de isolamento por teste
-----------------------------------
Cada test function recebe uma sessão envolvida em uma transação que
é revertida ao final (ROLLBACK), independente do resultado do teste.
Isso garante isolamento sem recriar tabelas entre testes, mantendo
a suite rápida mesmo com muitos testes.
"""

import os
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import app.models.cliente  # noqa: F401
import app.models.processed_event  # noqa: F401
from app.db.base import Base

TEST_DATABASE_URL: str = os.environ.get("TEST_DATABASE_URL")

# NullPool: desativa connection pooling nos testes.
# Cada operação abre e fecha sua própria conexão — sem estado vazando entre testes.
_test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Cria todas as tabelas uma vez por sessão de testes e as remove ao final.
    Não usa Alembic: Base.metadata.create_all basta para testes e não exige
    banco de migrations paralelo.
    """
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture()
async def connection() -> AsyncGenerator[AsyncConnection, None]:
    """
    Conexão com transação aberta e não commitada.
    O rollback ao final garante que cada teste parte de banco limpo.
    """
    async with _test_engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()


@pytest_asyncio.fixture()
async def db_session(connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """
    Sessão SQLAlchemy vinculada à conexão transacional do fixture `connection`.
    Injetar este fixture em qualquer teste garante isolamento automático.

    Uso:
        async def test_exemplo(db_session: AsyncSession):
            db_session.add(Cliente(...))
            await db_session.flush()
            result = await db_session.execute(select(Cliente))
            ...
    """
    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with session_factory() as session:
        yield session
