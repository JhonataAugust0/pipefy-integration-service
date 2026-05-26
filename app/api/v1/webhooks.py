"""
Router — Webhooks Pipefy (POST /webhooks/pipefy/card-updated)

Camada de transporte HTTP para eventos recebidos do Pipefy.
"""

import logging

from fastapi import APIRouter, status

from app.api.deps import WebhookServiceDep
from app.schemas.webhook import WebhookPayload, WebhookResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/pipefy/card-updated",
    status_code=status.HTTP_200_OK,
    summary="Recebe notificação de card atualizado do Pipefy",
    description=(
        "Endpoint de webhook. Verifica idempotência por event_id, "
        "calcula prioridade com base no patrimônio do cliente (RF-08) "
        "e estrutura a mutation updateCardField para o Pipefy."
    ),
)
async def post_card_updated(
    payload: WebhookPayload,
    service: WebhookServiceDep,
) -> WebhookResponse:
    """
    Endpoint RF-05 / RF-06 / RF-07 / RF-08 / RF-09 / RF-10.

    Fluxo:
      1. Pydantic valida payload (event_id, card_id, cliente_email, timestamp)
      2. Service verifica idempotência e processa o evento
      3. Retorna estado atual com flag idempotent
    """
    return await service.process_webhook(payload)
