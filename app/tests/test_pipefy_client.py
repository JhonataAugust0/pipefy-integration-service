"""
Pipefy Client (Mock) e Mutations

Foco: comportamento do client (send_mutation) e validade do contrato
entre service e client. Não testa substrings de constantes — testa
se o client despacha, responde e falha corretamente.
"""

from app.integrations.pipefy.client import send_mutation
from app.integrations.pipefy.mutations import (
    CREATE_CARD_MUTATION,
    UPDATE_CARD_FIELD_MUTATION,
)

CREATE_CARD_VARIABLES = {
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

UPDATE_CARD_VARIABLES = {
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


# ===================================================================
# send_mutation — createCard
# ===================================================================


class TestSendMutationCreateCard:
    """Valida que send_mutation com CREATE_CARD_MUTATION retorna resposta
    com a estrutura que o cliente_service consome (card.id, card.title)."""

    def test_returns_card_id_and_title(self):
        """O service extrai card.id e card.title da resposta para persistir
        pipefy_card_id. Se essa estrutura quebrar, o fluxo de criação falha."""
        response = send_mutation(CREATE_CARD_MUTATION, CREATE_CARD_VARIABLES)

        card = response["data"]["createCard"]["card"]
        assert card["id"] is not None
        assert card["title"] == "João Silva"

    def test_title_reflects_input_variable(self):
        """O title retornado deve espelhar o que o service enviou,
        garantindo rastreabilidade entre o cliente criado e o card."""
        variables = {
            "input": {
                **CREATE_CARD_VARIABLES["input"],
                "title": "Maria Souza",
            }
        }
        response = send_mutation(CREATE_CARD_MUTATION, variables)
        assert response["data"]["createCard"]["card"]["title"] == "Maria Souza"


# ===================================================================
# send_mutation — updateCardField
# ===================================================================


class TestSendMutationUpdateCardField:
    """Valida que send_mutation com UPDATE_CARD_FIELD_MUTATION retorna
    success para ambos os aliases (updateStatus e updatePrioridade)."""

    def test_returns_success_for_both_aliases(self):
        """O webhook_service depende de success=True em ambos os aliases
        para confirmar que status e prioridade foram atualizados."""
        response = send_mutation(UPDATE_CARD_FIELD_MUTATION, UPDATE_CARD_VARIABLES)

        assert response["data"]["updateStatus"]["success"] is True
        assert response["data"]["updatePrioridade"]["success"] is True


# ===================================================================
# send_mutation — fallback para mutation desconhecida
# ===================================================================


class TestSendMutationFallback:
    """Valida o comportamento de send_mutation com mutations não registradas."""

    def test_unknown_mutation_returns_error_structure(self):
        """Mutation não registrada deve retornar data=None + errors,
        impedindo que o service trate como sucesso silencioso."""
        response = send_mutation("mutation { unknown { id } }", {})

        assert response["data"] is None
        assert len(response["errors"]) > 0


# ===================================================================
# Contrato de variáveis createCard (critério de aceite Etapa 2)
# ===================================================================


class TestCreateCardVariablesContract:
    """
    Critério de aceite Etapa 2: a mutation createCard deve ser usada
    com variáveis que contenham name (title), email e patrimônio.

    Valida o contrato end-to-end: variáveis corretas → mock aceita
    e retorna resposta consumível pelo service.
    """

    def test_variables_with_name_email_patrimonio_produce_valid_response(self):
        """Variáveis com os 3 campos obrigatórios devem produzir
        uma resposta com card.id — campo que o service persiste."""
        response = send_mutation(CREATE_CARD_MUTATION, CREATE_CARD_VARIABLES)

        field_ids = [
            f["field_id"]
            for f in CREATE_CARD_VARIABLES["input"]["fields_attributes"]
        ]
        assert "email" in field_ids
        assert "patrimonio" in field_ids
        assert CREATE_CARD_VARIABLES["input"]["title"]  # name via title
        assert response["data"]["createCard"]["card"]["id"] is not None
