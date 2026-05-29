"""
Camada de Aplicação — Cliente Service

Orquestra o caso de uso US-01 (Criação de Cliente):
  1. Persistir cliente no banco com status "Aguardando Análise"
  2. Montar variáveis da mutation createCard
  3. Enviar mutation via pipefy client
  4. Persistir o pipefy_card_id retornado
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.domain.exceptions import EmailJaCadastradoError, PipefyIntegrationError
from app.integrations.pipefy.client import send_mutation
from app.integrations.pipefy.mutations import CREATE_CARD_MUTATION
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate

logger = logging.getLogger(__name__)

_settings = get_settings()
PIPEFY_PIPE_ID: str = _settings.PIPEFY_PIPE_ID
PIPEFY_PHASE_ID: str = _settings.PIPEFY_PHASE_ID


def _build_create_card_variables(cliente: Cliente) -> dict:
    """
    Monta as variáveis da mutation createCard conforme seção 2.4 do README.

    Responsabilidade: traduzir o modelo de domínio para o contrato GraphQL
    do Pipefy.
    """
    return {
        "input": {
            "pipe_id": PIPEFY_PIPE_ID,
            "title": cliente.cliente_nome,
            "fields_attributes": [
                {"field_id": "email", "field_value": [cliente.cliente_email]},
                {
                    "field_id": "patrimonio",
                    "field_value": [str(cliente.valor_patrimonio)],
                },
                {"field_id": "tipo", "field_value": [cliente.tipo_solicitacao]},
            ],
            "phase_id": PIPEFY_PHASE_ID,
        }
    }


class ClienteService:
    """
    Service injetável via Depends() na camada de transporte.

    Recebe a sessão do banco via construtor.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_cliente(self, payload: ClienteCreate) -> Cliente:
        """Ponto de entrada do orquestrador (Caso de uso US-01)."""
        await self._validate_email_uniqueness(payload.cliente_email)

        cliente = await self._persist_initial_cliente(payload)

        card_id = await self._create_pipefy_card(cliente)

        cliente.pipefy_card_id = card_id

        logger.info(
            "Cliente criado com sucesso: id=%s, email=%s, pipefy_card_id=%s",
            cliente.id,
            cliente.cliente_email,
            cliente.pipefy_card_id,
        )

        return cliente

    async def _validate_email_uniqueness(self, email: str) -> None:
        """
        Valida estado no banco de dados: lança EmailJaCadastradoError
        se encontrar duplicata.
        """
        email_exists = await self._session.execute(
            select(Cliente).where(Cliente.cliente_email == email)
        )
        if email_exists.scalar_one_or_none():
            raise EmailJaCadastradoError(email=email)

    async def _persist_initial_cliente(self, payload: ClienteCreate) -> Cliente:
        """
        Cria a entidade no banco de dados.
        Retorna a instância recém-criada com o ID gerado pelo DB.
        """
        cliente = Cliente(
            cliente_nome=payload.cliente_nome,
            cliente_email=payload.cliente_email,
            tipo_solicitacao=payload.tipo_solicitacao,
            valor_patrimonio=payload.valor_patrimonio,
            status="Aguardando Análise",
        )
        self._session.add(cliente)
        await self._session.flush()
        return cliente

    async def _create_pipefy_card(self, cliente: Cliente) -> str:
        """
        Envia a mutation, trata a resposta HTTP/GraphQL e devolve apenas o card_id.
        """
        variables = _build_create_card_variables(cliente)
        response = await send_mutation(CREATE_CARD_MUTATION, variables)

        if response and response.get("errors"):
            raise PipefyIntegrationError(
                message="A API do Pipefy recusou a criação do card.",
                details=response["errors"],
            )

        card_id = (
            response.get("data", {}).get("createCard", {}).get("card", {}).get("id")
        )

        if not card_id:
            raise PipefyIntegrationError(message="Card ID não retornado pelo Pipefy.")

        return card_id
