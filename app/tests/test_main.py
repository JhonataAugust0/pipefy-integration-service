"""
Testes — Infraestrutura da Aplicação (Health Check + Error Handlers)

Testa os componentes de infraestrutura HTTP que protegem a aplicação:
  - Health check com verificação real de conectividade com o banco
  - Exception handlers globais que convertem erros de domínio em HTTP
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Valida o deep health check (readiness probe) com verificação de banco."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_with_db(
        self, async_client: AsyncClient
    ):
        """
        O health check real executa SELECT 1 no banco.
        Com o db_session do fixture, a conexão é válida → status healthy.
        """
        response = await async_client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["dependencies"]["database"] == "healthy"


class TestExceptionHandlers:
    """Valida que os exception handlers convertem erros corretamente."""

    @pytest.mark.asyncio
    async def test_validation_error_returns_422_with_structured_body(
        self, async_client: AsyncClient
    ):
        """
        Payload malformado no POST /clientes deve retornar 422 com a
        mensagem padronizada do exception handler e a lista de erros.
        Testa o handler real no fluxo real — sem rotas dummy.
        """
        response = await async_client.post("/clientes", json={"cliente_nome": "Test"})

        assert response.status_code == 422
        body = response.json()
        assert body["message"] == (
            "Contrato de integração violado. Verifique o payload enviado."
        )
        assert "errors" in body
        assert len(body["errors"]) > 0
