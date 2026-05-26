"""
Testes de integração — WebhookService

Requerem PostgreSQL real (db-test, porta 5433).
Cada teste roda em transação revertida ao final
sem recriar schema entre testes (ver conftest.py).

Cobertura dos três casos obrigatórios do desafio:
  (a) patrimônio >= 200k → prioridade_alta
  (b) patrimônio < 200k  → prioridade_normal
  (c) event_id duplicado → HTTP 200, idempotent=True, sem escrita
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ClienteNaoEncontradoError
from app.models.cliente import Cliente
from app.schemas.webhook import WebhookPayload
from app.services.webhook_service import WebhookService

# ===================================================================
# Helpers
# ===================================================================


def _make_cliente(email: str, valor_patrimonio: float) -> Cliente:
    """Cria instância de Cliente sem persistir. Sem ID ainda."""
    return Cliente(
        cliente_nome="Teste",
        cliente_email=email,
        tipo_solicitacao="Teste",
        valor_patrimonio=valor_patrimonio,
        status="Aguardando Análise",
    )


def _make_payload(
    event_id: str, email: str, card_id: str = "card_001"
) -> WebhookPayload:
    return WebhookPayload(
        event_id=event_id,
        card_id=card_id,
        cliente_email=email,
        timestamp=datetime.now(timezone.utc),
    )


# ===================================================================
# (a) Regra de prioridade — patrimônio >= 200k
# ===================================================================


class TestPrioridadeAlta:
    @pytest.mark.asyncio
    async def test_patrimonio_acima_threshold_define_prioridade_alta(
        self, db_session: AsyncSession
    ):
        """RF-08 (a): 250_000 >= 200_000 → prioridade_alta."""
        cliente = _make_cliente("alta@example.com", 250_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        response = await service.process_webhook(
            _make_payload("evt_alta_001", "alta@example.com")
        )

        assert response.prioridade == "prioridade_alta"
        assert response.status == "Processado"
        assert response.idempotent is False

    @pytest.mark.asyncio
    async def test_patrimonio_exatamente_no_threshold_define_prioridade_alta(
        self, db_session: AsyncSession
    ):
        """RF-08 boundary: 200_000 exato → prioridade_alta."""
        cliente = _make_cliente("boundary@example.com", 200_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        response = await service.process_webhook(
            _make_payload("evt_boundary_001", "boundary@example.com")
        )

        assert response.prioridade == "prioridade_alta"

    @pytest.mark.asyncio
    async def test_modelo_cliente_atualizado_na_sessao_apos_processamento(
        self, db_session: AsyncSession
    ):
        """
        Verifica que os campos do modelo Cliente foram mutados na sessão
        após process_webhook — sem precisar de commit ou re-query.
        """
        cliente = _make_cliente("check@example.com", 300_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        await service.process_webhook(
            _make_payload("evt_check_001", "check@example.com")
        )

        # Verifica mutação direta no objeto ORM (identidade SQLAlchemy)
        assert cliente.status == "Processado"
        assert cliente.prioridade == "prioridade_alta"


# ===================================================================
# (b) Regra de prioridade — patrimônio < 200k
# ===================================================================


class TestPrioridadeNormal:
    @pytest.mark.asyncio
    async def test_patrimonio_abaixo_threshold_define_prioridade_normal(
        self, db_session: AsyncSession
    ):
        """RF-08 (b): 150_000 < 200_000 → prioridade_normal."""
        cliente = _make_cliente("normal@example.com", 150_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        response = await service.process_webhook(
            _make_payload("evt_normal_001", "normal@example.com")
        )

        assert response.prioridade == "prioridade_normal"
        assert response.status == "Processado"
        assert response.idempotent is False

    @pytest.mark.asyncio
    async def test_patrimonio_um_centavo_abaixo_define_prioridade_normal(
        self, db_session: AsyncSession
    ):
        """RF-08 boundary: 199_999.99 < 200_000 → prioridade_normal."""
        cliente = _make_cliente("centavo@example.com", 199_999.99)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        response = await service.process_webhook(
            _make_payload("evt_centavo_001", "centavo@example.com")
        )

        assert response.prioridade == "prioridade_normal"


# ===================================================================
# (c) Idempotência — event_id duplicado
# ===================================================================


class TestIdempotencia:
    @pytest.mark.asyncio
    async def test_event_id_duplicado_retorna_idempotent_true(
        self, db_session: AsyncSession
    ):
        """
        RF-06 (c): segunda chamada com mesmo event_id → idempotent=True.

        Mecanismo: INSERT ON CONFLICT (event_id) DO NOTHING retorna
        rowcount=0 na segunda execução dentro da mesma transação,
        porque o registro inserido na primeira chamada é visível
        na mesma transação (sem necessidade de commit).
        """
        cliente = _make_cliente("idem@example.com", 300_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        payload = _make_payload("evt_dup_001", "idem@example.com")

        # Primeira chamada: processa normalmente
        first = await service.process_webhook(payload)
        assert first.idempotent is False
        assert first.status == "Processado"

        # Segunda chamada com mesmo event_id: deve retornar idempotente
        second = await service.process_webhook(payload)
        assert second.idempotent is True
        assert second.event_id == payload.event_id

    @pytest.mark.asyncio
    async def test_event_id_duplicado_nao_altera_estado_do_cliente(
        self, db_session: AsyncSession
    ):
        """
        RF-06: após chamada idempotente, o cliente não deve ter sido
        modificado novamente. O status permanece o mesmo da primeira chamada.
        """
        cliente = _make_cliente("idem2@example.com", 150_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)
        payload = _make_payload("evt_dup_002", "idem2@example.com")

        await service.process_webhook(payload)
        status_apos_primeira_chamada = cliente.status

        # Forçar uma mutação no cliente para verificar que a segunda
        # chamada NÃO a sobrescreve (seria visível na sessão imediatamente)
        cliente.prioridade = "VALOR_SENTINELA"

        await service.process_webhook(payload)

        # Prioridade deve permanecer como "VALOR_SENTINELA" (não foi reescrita)
        assert cliente.prioridade == "VALOR_SENTINELA"
        assert cliente.status == status_apos_primeira_chamada

    @pytest.mark.asyncio
    async def test_dois_event_ids_distintos_sao_processados_independentemente(
        self, db_session: AsyncSession
    ):
        """
        Garante que a idempotência é por event_id, não por cliente.
        Dois webhooks com event_ids diferentes para o mesmo cliente
        devem ser processados normalmente.
        """
        cliente = _make_cliente("dois@example.com", 250_000)
        db_session.add(cliente)
        await db_session.flush()

        service = WebhookService(session=db_session)

        first = await service.process_webhook(
            _make_payload("evt_dois_001", "dois@example.com")
        )
        second = await service.process_webhook(
            _make_payload("evt_dois_002", "dois@example.com")
        )

        assert first.idempotent is False
        assert second.idempotent is False


# ===================================================================
# Casos de erro
# ===================================================================


class TestCasosDeErro:
    @pytest.mark.asyncio
    async def test_cliente_inexistente_levanta_cliente_nao_encontrado_error(
        self, db_session: AsyncSession
    ):
        """
        RF-07: webhook para e-mail sem cadastro no banco deve levantar
        ClienteNaoEncontradoError (convertida em HTTP 404 pelo router).
        """
        service = WebhookService(session=db_session)

        with pytest.raises(ClienteNaoEncontradoError) as exc_info:
            await service.process_webhook(
                _make_payload("evt_404_001", "inexistente@example.com")
            )

        assert "inexistente@example.com" in str(exc_info.value)
