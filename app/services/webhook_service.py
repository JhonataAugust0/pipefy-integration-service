"""
Camada de Aplicação — Webhook Service

Orquestra o caso de uso US-02 (Processamento de Webhook).
Refatorado com SRP: o método público age apenas como maestro,
delegando as regras de banco e negócio para funções privadas.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ClienteNaoEncontradoError, PipefyIntegrationError
from app.domain.priority import calculate_priority
from app.integrations.pipefy.client import send_mutation
from app.integrations.pipefy.mutations import UPDATE_CARD_FIELD_MUTATION
from app.models.cliente import Cliente
from app.models.processed_event import ProcessedEvent
from app.schemas.webhook import WebhookPayload, WebhookResponse

logger = logging.getLogger(__name__)


def _build_update_variables(card_id: str, prioridade: str) -> dict:
    """Monta as variáveis da mutation updateCardField com aliasing GraphQL."""
    return {
        "inputStatus": {
            "card_id": card_id,
            "field_id": "status",
            "new_value": ["Processado"],
        },
        "inputPrioridade": {
            "card_id": card_id,
            "field_id": "prioridade",
            "new_value": [prioridade],
        },
    }


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process_webhook(self, payload: WebhookPayload) -> WebhookResponse:
        """
        Ponto de entrada do orquestrador (Caso de uso US-02).
        Responsabilidade: Ditar o fluxo principal (Idempotência -> Negócio).
        """
        is_new_event = await self._register_event(payload.event_id)

        if not is_new_event:
            return await self._handle_duplicate_event(payload)

        return await self._process_new_event(payload)

    async def _register_event(self, event_id: str) -> bool:
        """
        Tenta inserir o event_id. Retorna True se for inédito, False se conflitar.
        """
        stmt = (
            pg_insert(ProcessedEvent)
            .values(event_id=event_id)
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def _handle_duplicate_event(self, payload: WebhookPayload) -> WebhookResponse:
        """Monta a resposta segura para eventos já processados."""
        logger.info(
            "[WEBHOOK] event_id=%s ja processado. Retornando resposta idempotente.",
            payload.event_id,
        )

        cliente = await self._get_cliente(payload.cliente_email)
        return WebhookResponse(
            event_id=payload.event_id,
            status=cliente.status if cliente else "desconhecido",
            prioridade=cliente.prioridade if cliente else None,
            idempotent=True,
        )

    async def _process_new_event(self, payload: WebhookPayload) -> WebhookResponse:
        """
        Executa a regra de negócio central da Mundo Invest:
        Busca cliente, calcula prioridade, atualiza banco local e avisa ao Pipefy.
        """
        cliente = await self._get_cliente(payload.cliente_email)

        if cliente is None:
            raise ClienteNaoEncontradoError(email=payload.cliente_email)

        prioridade = calculate_priority(cliente.valor_patrimonio)

        cliente.status = "Processado"
        cliente.prioridade = prioridade
        await self._session.flush()

        # Chamada Externa (GraphQL Mock)
        variables = _build_update_variables(payload.card_id, prioridade)
        response = send_mutation(UPDATE_CARD_FIELD_MUTATION, variables)

        if response and response.get("errors"):
            raise PipefyIntegrationError(
                message="Falha ao atualizar campos customizados no Pipefy.",
                details=response["errors"],
            )

        logger.info(
            "[WEBHOOK] Processado com sucesso: event_id=%s, email=%s, prioridade=%s",
            payload.event_id,
            payload.cliente_email,
            prioridade,
        )

        return WebhookResponse(
            event_id=payload.event_id,
            status=cliente.status,
            prioridade=cliente.prioridade,
            idempotent=False,
        )

    async def _get_cliente(self, email: str) -> Optional[Cliente]:
        """Busca cliente por e-mail no banco de dados."""
        result = await self._session.execute(
            select(Cliente).where(Cliente.cliente_email == email)
        )
        return result.scalar_one_or_none()
