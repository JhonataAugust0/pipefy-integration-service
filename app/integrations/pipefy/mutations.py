"""
Mutations GraphQL do Pipefy

Strings das mutations seguindo rigorosamente a documentação oficial:
https://api-docs.pipefy.com/

Cada mutation é exportada como constante para ser consumida pelo `client.py`.
Isolá-las permite revisão e diff de contrato GraphQL sem alterar o client.
"""

# ---------------------------------------------------------------------------
# createCard — Disparada em POST /clientes
# ---------------------------------------------------------------------------
# Cria um novo card no pipe do Pipefy com os dados do cliente.
# Retorna apenas o ID, título e URL para evitar over-fetching de rede.
#
# Variáveis esperadas pelo service:
#   - input.pipe_id        (env: PIPEFY_PIPE_ID)
#   - input.title          (cliente_nome)
#   - input.phase_id       (env: PIPEFY_PHASE_ID)
#   - input.fields_attributes:
#       - field_id: "email"      → ["cliente_email"] (Sempre em Array!)
#       - field_id: "patrimonio" → ["valor_patrimonio"]
#       - field_id: "tipo"       → ["tipo_solicitacao"]
# ---------------------------------------------------------------------------

CREATE_CARD_MUTATION: str = """
mutation createCard($input: CreateCardInput!) {
  createCard(input: $input) {
    card {
      id
      title
      url
    }
  }
}
""".strip()

# ---------------------------------------------------------------------------
# updateCardField — Disparada em POST /webhooks/pipefy/card-updated
# ---------------------------------------------------------------------------
# Atualiza status e prioridade do card usando aliasing GraphQL.
# A especificação GraphQL garante execução sequencial para mutations
# no mesmo documento, então updateStatus executa antes de updatePrioridade.
#
# Variáveis esperadas pelo service:
#   - inputStatus.card_id       → card_id do webhook
#   - inputStatus.field_id      → "status"
#   - inputStatus.new_value     → ["Processado"]
#   - inputPrioridade.card_id   → card_id do webhook
#   - inputPrioridade.field_id  → "prioridade"
#   - inputPrioridade.new_value → ["prioridade_alta"] ou ["prioridade_normal"]
# ---------------------------------------------------------------------------

UPDATE_CARD_FIELD_MUTATION: str = """
mutation updateCardFields(
  $inputStatus:    UpdateCardFieldInput!,
  $inputPrioridade: UpdateCardFieldInput!
) {
  updateStatus: updateCardField(input: $inputStatus) {
    clientMutationId
    success
  }
  updatePrioridade: updateCardField(input: $inputPrioridade) {
    clientMutationId
    success
  }
}
""".strip()