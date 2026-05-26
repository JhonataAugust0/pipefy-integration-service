"""
Injeção de Dependências:

Centraliza as dependências compartilhadas entre os routers.
O FastAPI injeta estas dependências via `Depends()` em cada rota.

Nenhum router importa diretamente de db/ ou services/, todas as
dependências passam por este módulo.

Tipo Annotated (PEP 593):
  FastAPI >= 0.95 recomenda Annotated em vez de valores default
  com Depends(). Isso separa tipo de metadado de DI, melhora
  a legibilidade e evita conflitos com linters estáticos.
"""

from typing import Annotated, AsyncGenerator, TypeAlias

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.cliente_service import ClienteService
from app.services.webhook_service import WebhookService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Centraliza a dependência de sessão neste módulo para que
    os routers importem apenas de deps.py, sem acoplamento
    direto ao módulo de infraestrutura db/session.py.
    """
    async for session in get_db():
        yield session


def get_cliente_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClienteService:
    """
    Factory de dependência para o ClienteService.

    O FastAPI resolve: get_session → session → ClienteService.
    O router recebe o service pronto, sem saber como ele foi construído.
    """
    return ClienteService(session=session)


def get_webhook_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WebhookService:
    """
    Factory de dependência para o WebhookService.
    O FastAPI resolve: get_session → session → WebhookService.
    """
    return WebhookService(session=session)


# Type aliases reutilizáveis pelos routers
SessionDep: TypeAlias = Annotated[AsyncSession, Depends(get_session)]
ClienteServiceDep: TypeAlias = Annotated[ClienteService, Depends(get_cliente_service)]
WebhookServiceDep: TypeAlias = Annotated[WebhookService, Depends(get_webhook_service)]
