"""
Camada de Aplicação — Cliente Service

Orquestra o caso de uso US-01 (Criação de Cliente):
  1. Persistir cliente no banco com status "Aguardando Análise"
  2. Montar variáveis da mutation createCard
  3. Enviar mutation via pipefy client
  4. Persistir o pipefy_card_id retornado
"""

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.pipefy.client import send_mutation
from app.integrations.pipefy.mutations import CREATE_CARD_MUTATION
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate

logger = logging.getLogger(__name__)

PIPEFY_PIPE_ID: str = os.environ.get("PIPEFY_PIPE_ID", "000000")
PIPEFY_PHASE_ID: str = os.environ.get("PIPEFY_PHASE_ID", "000000")


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
        """
        Caso de uso: criação de cliente (US-01).

        Fluxo:
          1. Cria o registro no banco com status "Aguardando Análise"
          2. Flush para obter o ID gerado pelo banco
          3. Monta e envia a mutation createCard ao Pipefy (mock)
          4. Persiste o pipefy_card_id retornado

        Args:
            payload: Dados validados pelo schema ClienteCreate.

        Returns:
            Instância do modelo Cliente com todos os campos preenchidos.
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

        variables = _build_create_card_variables(cliente)
        response = send_mutation(CREATE_CARD_MUTATION, variables)

        card_id = (
            response.get("data", {}).get("createCard", {}).get("card", {}).get("id")
        )
        if card_id:
            cliente.pipefy_card_id = card_id

        logger.info(
            "Cliente criado: id=%s, email=%s, pipefy_card_id=%s",
            cliente.id,
            cliente.cliente_email,
            cliente.pipefy_card_id,
        )

        return cliente
