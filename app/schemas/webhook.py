"""
Schemas Pydantic — Webhook

Contratos de entrada e saída para POST /webhooks/pipefy/card-updated.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class WebhookPayload(BaseModel):
    """
    Payload recebido do Pipefy quando um card é atualizado (RF-05).
    O sistema rejeita processamento duplicado baseado no event_id
    (Idempotência RF-06).
    """

    event_id: str = Field(
        ...,
        description="Identificador único do evento. Usado para controle" \
        "de idempotência.",
        examples=["evt_123"],
    )
    card_id: str = Field(
        ...,
        description="ID do card no Pipefy. Usado nas variáveis de updateCardField.",
        examples=["card_456"],
    )
    cliente_email: EmailStr = Field(
        ...,
        description="E-mail do cliente associado ao card. Chave de busca no banco.",
        examples=["joao.silva@example.com"],
    )
    timestamp: datetime = Field(
        ...,
        description="Momento em que o evento foi gerado pelo Pipefy.",
        examples=["2026-05-18T12:00:00Z"],
    )


class WebhookResponse(BaseModel):
    """
    Resposta de POST /webhooks/pipefy/card-updated (HTTP 200).

    O campo `idempotent` indica se o evento já havia sido processado
    anteriormente. Quando True, nenhuma escrita foi realizada no banco.
    """

    event_id: str
    status: str
    prioridade: Optional[str] = None
    idempotent: bool = Field(
        description="True se o event_id já havia sido processado. "
        "Nenhuma escrita realizada.",
    )
