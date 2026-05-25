"""
Testes de integração — POST /clientes (US-01)

Cenários BDD da seção 1.4 do README:
  (a) Criação com payload válido → HTTP 201, persistência, status e card_id
  (b) Payload com e-mail inválido → HTTP 422, nada persistido
  (c) Payload com campo obrigatório ausente → HTTP 422

Todos os testes usam o fixture async_client com sessão transacional
(rollback automático ao final de cada teste).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente

VALID_PAYLOAD = {
    "cliente_nome": "João Silva",
    "cliente_email": "joao.silva@example.com",
    "tipo_solicitacao": "Atualização cadastral",
    "valor_patrimonio": 250000.00,
}


# ===================================================================
# (a) Criação de cliente com payload válido
# ===================================================================


class TestCriacaoClienteValido:
    """Scenario: Criação de cliente com payload válido (BDD US-01)."""

    @pytest.mark.asyncio
    async def test_creates_client_with_correct_state(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """
        RF-01/RF-02/RF-03/RF-04 em um único fluxo:
        POST válido → 201 + corpo correto + persistido com status
        'Aguardando Análise' + pipefy_card_id preenchido pelo mock.
        """
        response = await async_client.post("/clientes", json=VALID_PAYLOAD)

        assert response.status_code == 201

        body = response.json()
        assert body["cliente_nome"] == "João Silva"
        assert body["cliente_email"] == "joao.silva@example.com"
        assert body["status"] == "Aguardando Análise"
        assert body["pipefy_mutation_sent"] == "createCard"

        result = await db_session.execute(
            select(Cliente).where(Cliente.id == body["id"])
        )
        cliente = result.scalar_one()

        assert cliente.status == "Aguardando Análise"
        assert cliente.valor_patrimonio == 250000.00
        assert cliente.pipefy_card_id is not None


# ===================================================================
# (b) Payload com e-mail inválido
# ===================================================================


class TestCriacaoClienteEmailInvalido:
    """Scenario: Criação de cliente com e-mail inválido (BDD US-01)."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_email_without_persisting(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """
        RF-02: e-mail inválido → 422, nenhum registro no banco.
        Verifica tanto a rejeição HTTP quanto a ausência de side-effect.
        """
        payload = {**VALID_PAYLOAD, "cliente_email": "email-invalido"}
        response = await async_client.post("/clientes", json=payload)

        assert response.status_code == 422

        result = await db_session.execute(select(Cliente))
        assert result.scalar_one_or_none() is None


# ===================================================================
# (c) Payload com campo obrigatório ausente
# ===================================================================


class TestCriacaoClienteCampoAusente:
    """Scenario: Criação de cliente com campo obrigatório ausente (BDD US-01)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("campo_ausente", [
        "cliente_nome",
        "cliente_email",
        "tipo_solicitacao",
        "valor_patrimonio",
    ])
    async def test_rejects_missing_required_field(
        self, async_client: AsyncClient, campo_ausente: str
    ):
        """RF-02: qualquer campo obrigatório ausente → 422."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != campo_ausente}
        response = await async_client.post("/clientes", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_field_does_not_persist(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Validação falha → nenhum side-effect no banco."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "cliente_nome"}
        await async_client.post("/clientes", json=payload)

        result = await db_session.execute(select(Cliente))
        assert result.scalar_one_or_none() is None
