"""
Injeção de Dependências:

Centraliza as dependências compartilhadas entre os routers.
O FastAPI injeta estas dependências via `Depends()` em cada rota.

Nenhum router importa diretamente de db/ ou services/, todas as
dependências passam por este módulo.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.cliente_service import ClienteService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Centraliza a dependência de sessão neste módulo para que
    os routers importem apenas de deps.py, sem acoplamento
    direto ao módulo de infraestrutura db/session.py.
    """
    async for session in get_db():
        yield session


async def get_cliente_service(
    session: AsyncSession = Depends(get_session),
) -> ClienteService:
    """
    Factory de dependência para o ClienteService.

    O FastAPI resolve a cadeia: get_session → session → ClienteService.
    O router recebe o service pronto, sem saber como ele foi construído.
    """
    return ClienteService(session=session)
