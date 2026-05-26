"""
Testes unitários — Mapeamento domínio→GraphQL e validação de schemas

Componentes testados:
  - _build_create_card_variables (cliente_service.py)
  - _build_update_variables (webhook_service.py)
  - ClienteCreate schema constraints (valor_patrimonio > 0, min_length)

Estes são testes unitários puros — sem banco, sem HTTP.
"""

import pytest
from pydantic import ValidationError

from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate
from app.services.cliente_service import _build_create_card_variables
from app.services.webhook_service import _build_update_variables

# ===================================================================
# _build_create_card_variables
# ===================================================================


class TestBuildCreateCardVariables:
    """
    Protege o contrato de mapeamento domínio→GraphQL do createCard.

    Se alguém mudar o field_id, o formato de array, ou esquecer de
    converter valor_patrimonio para string, estes testes quebram.
    """

    def _make_cliente(self) -> Cliente:
        return Cliente(
            id=1,
            cliente_nome="Ana Costa",
            cliente_email="ana@example.com",
            tipo_solicitacao="Consultoria",
            valor_patrimonio=350000.50,
            status="Aguardando Análise",
        )

    def test_title_maps_to_cliente_nome(self):
        """O title do card deve ser o nome do cliente."""
        variables = _build_create_card_variables(self._make_cliente())
        assert variables["input"]["title"] == "Ana Costa"

    def test_fields_attributes_contains_email_as_array(self):
        """
        A API do Pipefy exige field_value como array.
        Se alguém remover os colchetes, o Pipefy rejeita silenciosamente.
        """
        variables = _build_create_card_variables(self._make_cliente())
        fields = {
            f["field_id"]: f["field_value"]
            for f in variables["input"]["fields_attributes"]
        }

        assert fields["email"] == ["ana@example.com"]
        assert isinstance(fields["email"], list)

    def test_patrimonio_is_string_in_array(self):
        """
        O Pipefy espera field_value como [string]. O valor numérico
        deve ser convertido para string antes de ser enviado.
        """
        variables = _build_create_card_variables(self._make_cliente())
        fields = {
            f["field_id"]: f["field_value"]
            for f in variables["input"]["fields_attributes"]
        }

        assert fields["patrimonio"] == ["350000.5"]
        assert isinstance(fields["patrimonio"][0], str)

    def test_tipo_solicitacao_maps_to_field_tipo(self):
        """tipo_solicitacao do domínio deve mapear para field_id 'tipo'."""
        variables = _build_create_card_variables(self._make_cliente())
        fields = {
            f["field_id"]: f["field_value"]
            for f in variables["input"]["fields_attributes"]
        }

        assert fields["tipo"] == ["Consultoria"]

    def test_contains_pipe_id_and_phase_id(self):
        """pipe_id e phase_id devem estar presentes (vêm do env)."""
        variables = _build_create_card_variables(self._make_cliente())
        assert "pipe_id" in variables["input"]
        assert "phase_id" in variables["input"]


# ===================================================================
# _build_update_variables
# ===================================================================


class TestBuildUpdateVariables:
    """
    Protege o contrato de mapeamento para a mutation updateCardField.
    O aliasing GraphQL (inputStatus/inputPrioridade) é crítico —
    se as chaves mudarem, a mutation falha silenciosamente.
    """

    def test_status_alias_maps_correctly(self):
        """inputStatus deve conter field_id 'status' com new_value ['Processado']."""
        variables = _build_update_variables("card_123", "prioridade_alta")

        assert variables["inputStatus"]["card_id"] == "card_123"
        assert variables["inputStatus"]["field_id"] == "status"
        assert variables["inputStatus"]["new_value"] == ["Processado"]

    def test_prioridade_alias_maps_correctly(self):
        """inputPrioridade deve conter field_id 'prioridade' com o valor calculado."""
        variables = _build_update_variables("card_123", "prioridade_normal")

        assert variables["inputPrioridade"]["card_id"] == "card_123"
        assert variables["inputPrioridade"]["field_id"] == "prioridade"
        assert variables["inputPrioridade"]["new_value"] == ["prioridade_normal"]

    def test_new_value_is_always_array(self):
        """
        A API do Pipefy exige new_value como array.
        Ambos os aliases devem usar formato de array.
        """
        variables = _build_update_variables("card_x", "prioridade_alta")

        assert isinstance(variables["inputStatus"]["new_value"], list)
        assert isinstance(variables["inputPrioridade"]["new_value"], list)


# ===================================================================
# ClienteCreate — validação de constraints do schema
# ===================================================================


class TestClienteCreateSchemaConstraints:
    """
    Testa as constraints do Pydantic que protegem a integridade dos dados
    antes de chegarem ao service. Foco nos edge cases que não são cobertos
    pelos testes de endpoint (que só testam 'campo ausente' e 'email inválido').
    """

    def test_valor_patrimonio_zero_is_rejected(self):
        """Schema exige gt=0. Patrimônio zero deve ser rejeitado."""
        with pytest.raises(ValidationError) as exc_info:
            ClienteCreate(
                cliente_nome="Test",
                cliente_email="t@t.com",
                tipo_solicitacao="Test",
                valor_patrimonio=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("valor_patrimonio",) for e in errors)

    def test_valor_patrimonio_negativo_is_rejected(self):
        """Patrimônio negativo é inválido."""
        with pytest.raises(ValidationError):
            ClienteCreate(
                cliente_nome="Test",
                cliente_email="t@t.com",
                tipo_solicitacao="Test",
                valor_patrimonio=-100,
            )

    def test_cliente_nome_vazio_is_rejected(self):
        """Schema exige min_length=1. String vazia deve ser rejeitada."""
        with pytest.raises(ValidationError) as exc_info:
            ClienteCreate(
                cliente_nome="",
                cliente_email="t@t.com",
                tipo_solicitacao="Test",
                valor_patrimonio=1000,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("cliente_nome",) for e in errors)

    def test_tipo_solicitacao_vazio_is_rejected(self):
        """tipo_solicitacao com string vazia deve ser rejeitada."""
        with pytest.raises(ValidationError):
            ClienteCreate(
                cliente_nome="Test",
                cliente_email="t@t.com",
                tipo_solicitacao="",
                valor_patrimonio=1000,
            )

    def test_valid_payload_creates_instance(self):
        """Sanity check: payload válido deve criar instância sem erro."""
        cliente = ClienteCreate(
            cliente_nome="João Silva",
            cliente_email="joao@example.com",
            tipo_solicitacao="Atualização cadastral",
            valor_patrimonio=250000.00,
        )

        assert cliente.cliente_nome == "João Silva"
        assert str(cliente.cliente_email) == "joao@example.com"
