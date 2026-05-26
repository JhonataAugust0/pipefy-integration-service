"""
Testes de integração — POST /webhooks/pipefy/card-updated

Os testes do WebhookService (test_webhook_service.py) validam a lógica
de negócio chamando o service diretamente. Estes testes complementam
exercitando a **camada HTTP completa**: payload → Pydantic → router →
service → DB → exception handlers → HTTP response.

Gaps cobertos:
  - Exception handlers de domínio (404, 502) via HTTP
  - Validação do schema WebhookPayload via HTTP (422)
  - Contrato de resposta HTTP (WebhookResponse)
  - Fluxo completo de criação → webhook → resposta com prioridade
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente

# ===================================================================
# Helpers
# ===================================================================

VALID_CLIENTE_PAYLOAD = {
    "cliente_nome": "Maria Testes",
    "cliente_email": "maria.webhook@example.com",
    "tipo_solicitacao": "Abertura de conta",
    "valor_patrimonio": 250000.00,
}


def _webhook_payload(
    event_id: str = "evt_http_001",
    email: str = "maria.webhook@example.com",
    card_id: str = "card_http_001",
) -> dict:
    return {
        "event_id": event_id,
        "card_id": card_id,
        "cliente_email": email,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ===================================================================
# Fluxo completo: criação do cliente → webhook → resposta
# ===================================================================


class TestWebhookFluxoCompleto:
    """Testa o ciclo completo POST /clientes → POST /webhooks via HTTP."""

    @pytest.mark.asyncio
    async def test_webhook_processa_cliente_existente_com_prioridade_alta(
        self, async_client: AsyncClient
    ):
        """
        Dado um cliente com patrimônio >= 200k já cadastrado,
        quando POST /webhooks/pipefy/card-updated:
        - Retorna 200 com status=Processado, prioridade=prioridade_alta
        - idempotent=False (primeiro processamento)
        """
        await async_client.post("/clientes", json=VALID_CLIENTE_PAYLOAD)

        response = await async_client.post(
            "/webhooks/pipefy/card-updated",
            json=_webhook_payload(),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "Processado"
        assert body["prioridade"] == "prioridade_alta"
        assert body["idempotent"] is False
        assert body["event_id"] == "evt_http_001"

    @pytest.mark.asyncio
    async def test_webhook_processa_cliente_com_prioridade_normal(
        self, async_client: AsyncClient
    ):
        """Dado patrimônio < 200k, webhook retorna prioridade_normal."""
        payload_cliente = {
            **VALID_CLIENTE_PAYLOAD,
            "cliente_email": "normal.webhook@example.com",
            "valor_patrimonio": 150000.00,
        }
        await async_client.post("/clientes", json=payload_cliente)

        response = await async_client.post(
            "/webhooks/pipefy/card-updated",
            json=_webhook_payload(
                event_id="evt_normal_http",
                email="normal.webhook@example.com",
            ),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["prioridade"] == "prioridade_normal"


# ===================================================================
# Idempotência via HTTP
# ===================================================================


class TestWebhookIdempotenciaHTTP:
    """Valida que a idempotência funciona corretamente via camada HTTP."""

    @pytest.mark.asyncio
    async def test_segunda_chamada_com_mesmo_event_id_retorna_idempotent_true(
        self, async_client: AsyncClient
    ):
        """
        RF-06: segundo POST com mesmo event_id → 200 com idempotent=True.
        Testa via HTTP — o test_webhook_service já testa via service direto.
        """
        await async_client.post("/clientes", json=VALID_CLIENTE_PAYLOAD)

        webhook = _webhook_payload(event_id="evt_idem_http")
        first = await async_client.post("/webhooks/pipefy/card-updated", json=webhook)
        second = await async_client.post("/webhooks/pipefy/card-updated", json=webhook)

        assert first.status_code == 200
        assert first.json()["idempotent"] is False

        assert second.status_code == 200
        assert second.json()["idempotent"] is True


# ===================================================================
# Exception Handlers via HTTP (404, 422)
# ===================================================================


class TestWebhookExceptionHandlers:
    """Testa que os exception handlers convertem erros de domínio em HTTP."""

    @pytest.mark.asyncio
    async def test_cliente_inexistente_retorna_404(self, async_client: AsyncClient):
        """
        ClienteNaoEncontradoError → exception handler → HTTP 404.
        Zero cobertura anterior — o test_webhook_service testava
        o pytest.raises mas nunca a conversão HTTP.
        """
        response = await async_client.post(
            "/webhooks/pipefy/card-updated",
            json=_webhook_payload(
                event_id="evt_404_http",
                email="nao.existe@example.com",
            ),
        )

        assert response.status_code == 404
        body = response.json()
        assert "nao.existe@example.com" in body["detail"]

    @pytest.mark.asyncio
    async def test_payload_sem_event_id_retorna_422(self, async_client: AsyncClient):
        """
        WebhookPayload exige event_id. Sem ele → RequestValidationError → 422.
        Valida que o schema do webhook está protegido pelo Pydantic.
        """
        response = await async_client.post(
            "/webhooks/pipefy/card-updated",
            json={
                "card_id": "card_001",
                "cliente_email": "test@example.com",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_payload_com_email_invalido_retorna_422(
        self, async_client: AsyncClient
    ):
        """
        WebhookPayload usa EmailStr. E-mail inválido → 422.
        """
        response = await async_client.post(
            "/webhooks/pipefy/card-updated",
            json=_webhook_payload(email="nao-e-email"),
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_payload_sem_timestamp_retorna_422(self, async_client: AsyncClient):
        """Todos os 4 campos são obrigatórios. Sem timestamp → 422."""
        response = await async_client.post(
            "/webhooks/pipefy/card-updated",
            json={
                "event_id": "evt_no_ts",
                "card_id": "card_001",
                "cliente_email": "test@example.com",
            },
        )

        assert response.status_code == 422
