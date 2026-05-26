"""
Testes de integração — POST /clientes

Cenários BDD da seção 1.4 do README (US-01):
  (a) Criação com payload válido → HTTP 201, persistência, status e card_id
  (b) Payload com e-mail inválido → HTTP 422, sem persistência
  (c) Payload com campo obrigatório ausente → HTTP 422 (parametrizado)
  (d) E-mail duplicado → HTTP 409 (EmailJaCadastradoError)
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
    async def test_creates_cliente_with_correct_response_and_persistence(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """
        Dado um payload válido, quando POST /clientes:
        - Retorna 201 com id, nome, email, status e mutation
        - Persiste no banco com status 'Aguardando Análise'
        - Preenche pipefy_card_id com o ID retornado pelo mock

        Consolida a validação do fluxo completo em um único teste
        para evitar 4 requests idênticas que testam a mesma operação.
        """
        response = await async_client.post("/clientes", json=VALID_PAYLOAD)

        # --- HTTP Response ---
        assert response.status_code == 201
        body = response.json()
        assert body["cliente_nome"] == "João Silva"
        assert body["cliente_email"] == "joao.silva@example.com"
        assert body["status"] == "Aguardando Análise"
        assert body["pipefy_mutation_sent"] == "createCard"

        # --- Persistência no banco ---
        result = await db_session.execute(
            select(Cliente).where(Cliente.id == body["id"])
        )
        cliente = result.scalar_one()

        assert cliente.status == "Aguardando Análise"
        assert cliente.cliente_nome == "João Silva"
        assert cliente.valor_patrimonio == pytest.approx(250000.00)
        assert cliente.pipefy_card_id is not None


# ===================================================================
# (b) Payload com e-mail inválido
# ===================================================================


class TestCriacaoClienteEmailInvalido:
    """Scenario: Criação de cliente com e-mail inválido (BDD US-01)."""

    @pytest.mark.asyncio
    async def test_email_invalido_returns_422_without_persistence(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """
        Dado e-mail inválido, o Pydantic rejeita na camada HTTP.
        Nenhum registro deve ser persistido — a request nem chega ao service.
        """
        payload = {**VALID_PAYLOAD, "cliente_email": "email-invalido"}
        response = await async_client.post("/clientes", json=payload)

        assert response.status_code == 422

        result = await db_session.execute(
            select(Cliente).where(Cliente.cliente_nome == "João Silva")
        )
        assert result.scalar_one_or_none() is None


# ===================================================================
# (c) Payload com campo obrigatório ausente (parametrizado)
# ===================================================================


class TestCriacaoClienteCampoAusente:
    """Scenario: Criação de cliente com campo obrigatório ausente (BDD US-01)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "campo_ausente",
        [
            "cliente_nome",
            "cliente_email",
            "tipo_solicitacao",
            "valor_patrimonio",
        ],
    )
    async def test_campo_obrigatorio_ausente_returns_422(
        self, async_client: AsyncClient, campo_ausente: str
    ):
        """
        Cada campo obrigatório ausente deve resultar em 422.
        Parametrizado para cobrir todos os campos sem duplicar código.
        """
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != campo_ausente}
        response = await async_client.post("/clientes", json=payload)
        assert response.status_code == 422


# ===================================================================
# (d) E-mail duplicado
# ===================================================================


class TestCriacaoClienteEmailDuplicado:
    """Cenário não-BDD mas essencial: unicidade de e-mail no banco."""

    @pytest.mark.asyncio
    async def test_email_duplicado_returns_409(self, async_client: AsyncClient):
        """
        Dado um cliente já cadastrado, ao enviar POST com o mesmo e-mail,
        o service deve lançar EmailJaCadastradoError → handler retorna 409.
        Protege a regra de unicidade e o exception handler de domínio.
        """
        await async_client.post("/clientes", json=VALID_PAYLOAD)

        payload_duplicado = {
            **VALID_PAYLOAD,
            "cliente_nome": "João Silva Jr",
        }
        response = await async_client.post("/clientes", json=payload_duplicado)

        assert response.status_code == 409
