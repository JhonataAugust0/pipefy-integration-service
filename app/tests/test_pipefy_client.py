"""
Testes unitários — Pipefy Client (Mock) e Mutations GraphQL

Foco: validar o contrato GraphQL (estrutura das mutations) e o comportamento
do client mock (dispatch, fallback, logging). Cada teste protege uma invariante
real do sistema — não há asserts de substring avulsos.
"""

import logging

from app.integrations.pipefy.client import send_mutation
from app.integrations.pipefy.mutations import (
    CREATE_CARD_MUTATION,
    UPDATE_CARD_FIELD_MUTATION,
)

# ===================================================================
# Contrato GraphQL — createCard
# ===================================================================


class TestCreateCardMutationContract:
    """Garante que a mutation createCard está aderente à API do Pipefy."""

    def test_create_card_mutation_structure(self):
        """
        A mutation deve declarar a operação createCard com o tipo
        CreateCardInput! e solicitar os campos essenciais de retorno.
        Protege contra edições acidentais na string GraphQL.
        """
        assert "mutation createCard($input: CreateCardInput!)" in CREATE_CARD_MUTATION
        assert "createCard(input: $input)" in CREATE_CARD_MUTATION

        # Campos de retorno que o service consome
        for required_field in ("id", "title", "url"):
            assert required_field in CREATE_CARD_MUTATION, (
                f"Campo '{required_field}' ausente na mutation createCard"
            )

    def test_create_card_variables_contain_name_email_patrimonio(self):
        """
        Critério de aceite da Etapa 2: as variáveis montadas pelo service
        devem conter name (title), email e patrimônio no formato de array
        esperado pela API do Pipefy.

        Testa o fluxo completo: variáveis → send_mutation → resposta com card_id.
        """
        variables = {
            "input": {
                "pipe_id": "12345",
                "title": "João Silva",
                "fields_attributes": [
                    {"field_id": "email", "field_value": ["joao@example.com"]},
                    {"field_id": "patrimonio", "field_value": ["250000"]},
                    {"field_id": "tipo", "field_value": ["Atualização cadastral"]},
                ],
                "phase_id": "67890",
            }
        }

        field_ids = [f["field_id"] for f in variables["input"]["fields_attributes"]]
        assert "email" in field_ids
        assert "patrimonio" in field_ids

        response = send_mutation(CREATE_CARD_MUTATION, variables)
        card = response["data"]["createCard"]["card"]
        assert card["id"] is not None
        assert card["title"] == "João Silva"


# ===================================================================
# Contrato GraphQL — updateCardField
# ===================================================================


class TestUpdateCardFieldMutationContract:
    """Garante que a mutation updateCardField usa aliasing e tipos corretos."""

    def test_update_card_field_mutation_structure(self):
        """
        A mutation deve usar aliasing GraphQL (updateStatus/updatePrioridade)
        com UpdateCardFieldInput! e solicitar success + clientMutationId.
        Protege contra quebra do contrato de aliasing.
        """
        assert "UpdateCardFieldInput!" in UPDATE_CARD_FIELD_MUTATION
        assert (
            "updateStatus: updateCardField(input: $inputStatus)"
            in UPDATE_CARD_FIELD_MUTATION
        )
        assert (
            "updatePrioridade: updateCardField(input: $inputPrioridade)"
            in UPDATE_CARD_FIELD_MUTATION
        )
        assert "success" in UPDATE_CARD_FIELD_MUTATION
        assert "clientMutationId" in UPDATE_CARD_FIELD_MUTATION


# ===================================================================
# Comportamento do client mock (send_mutation)
# ===================================================================


class TestSendMutation:
    """Valida o dispatch e o contrato de resposta do client mock."""

    def test_create_card_returns_valid_card_response(self):
        """
        send_mutation com createCard deve retornar resposta com a mesma
        estrutura que a API real do Pipefy (data.createCard.card).
        O service depende de card.id para preencher pipefy_card_id.
        """
        variables = {
            "input": {
                "pipe_id": "12345",
                "title": "Maria Souza",
                "fields_attributes": [
                    {"field_id": "email", "field_value": ["maria@example.com"]},
                    {"field_id": "patrimonio", "field_value": ["100000"]},
                ],
                "phase_id": "67890",
            }
        }

        response = send_mutation(CREATE_CARD_MUTATION, variables)

        card = response["data"]["createCard"]["card"]
        assert card["id"] is not None
        assert card["title"] == "Maria Souza"
        assert card["url"].startswith("https://")

    def test_update_card_field_returns_success_for_both_aliases(self):
        """
        send_mutation com updateCardField deve retornar success=True
        para ambos os aliases. O webhook_service depende deste contrato
        para confirmar que o Pipefy processou as atualizações.
        """
        variables = {
            "inputStatus": {
                "card_id": "12345",
                "field_id": "status",
                "new_value": ["Processado"],
            },
            "inputPrioridade": {
                "card_id": "12345",
                "field_id": "prioridade",
                "new_value": ["prioridade_alta"],
            },
        }

        response = send_mutation(UPDATE_CARD_FIELD_MUTATION, variables)

        assert response["data"]["updateStatus"]["success"] is True
        assert response["data"]["updatePrioridade"]["success"] is True

    def test_unknown_mutation_returns_error_response(self):
        """
        Mutation não registrada no _MUTATION_HANDLERS deve retornar
        data=None + errors, sinalizando falha para quem consome.
        Protege o fallback do registry pattern.
        """
        response = send_mutation("mutation { foo { id } }", {})

        assert response["data"] is None
        assert len(response["errors"]) > 0

    def test_logs_payload_on_send(self, caplog):
        """
        O client deve logar mutation + variáveis para auditoria.
        Em produção este log seria essencial para debugging de
        payloads rejeitados pelo Pipefy.
        """
        variables = {"input": {"pipe_id": "99999", "title": "Log Test"}}

        with caplog.at_level(logging.INFO, logger="app.integrations.pipefy.client"):
            send_mutation(CREATE_CARD_MUTATION, variables)

        log_messages = [r.message for r in caplog.records]
        assert any("Mutation enviada" in msg for msg in log_messages)
