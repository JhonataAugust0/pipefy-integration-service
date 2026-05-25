"""
Infraestrutura da aplicação (main.py)

Valida os endpoints de sistema e o exception handler global.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_health_check():
    """
    O /health é o contrato usado pelo Docker healthcheck e load balancer
    para determinar se a API está respondendo. Se quebrar, o container
    reinicia indefinidamente.
    """
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy", "service": "pipefy-integration-api"
    }


@pytest.mark.asyncio
async def test_validation_error_returns_custom_message():
    """
    O exception handler customizado garante que payloads malformados
    retornem a mensagem padronizada do contrato de integração,
    não o formato padrão do FastAPI. Isso importa porque o Pipefy
    (ou qualquer consumidor) precisa de uma resposta previsível.

    Usa o endpoint real POST /clientes com payload vazio para exercitar
    o handler sem criar rotas fantasma no app.
    """
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post("/clientes", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["message"] == "Contrato de integração violado. Verifique o payload "
    "enviado."
    assert len(body["errors"]) > 0
