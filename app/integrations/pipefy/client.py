"""
Pipefy GraphQL Client (Mock)

Simulação do cliente GraphQL do Pipefy para desenvolvimento local.
Em produção, `send_mutation` seria substituído por uma chamada HTTP real
(httpx.AsyncClient) sem alterar nenhuma outra camada da aplicação
(Ports & Adapters).

Refatorado para async: em produção, send_mutation fará I/O de rede
(HTTP POST para a API GraphQL do Pipefy). Manter a interface async
desde o mock evita refatorações futuras em toda a cadeia de chamadas.
"""

import logging
import uuid
from datetime import datetime, timezone

from app.integrations.pipefy.mutations import (
    CREATE_CARD_MUTATION,
    UPDATE_CARD_FIELD_MUTATION,
)

logger = logging.getLogger(__name__)

# Registry: mapeia cada mutation à sua função geradora de resposta mock.
# Ao adicionar uma nova mutation em mutations.py, basta registrar aqui
# a função correspondente — send_mutation não precisa ser alterado.
_MUTATION_HANDLERS: dict = {}


def _handle(mutation_constant: str):
    """Decorator que registra uma função geradora de resposta para uma mutation."""

    def decorator(fn):
        _MUTATION_HANDLERS[mutation_constant] = fn
        return fn

    return decorator


# ---------------------------------------------------------------
# Geradores de resposta mock
# ---------------------------------------------------------------


@_handle(CREATE_CARD_MUTATION)
def _mock_create_card_response(variables: dict) -> dict:
    """Gera resposta simulada para a mutation createCard."""
    simulated_card_id = str(uuid.uuid4().int)[:10]
    now = datetime.now(timezone.utc).isoformat()

    return {
        "data": {
            "createCard": {
                "card": {
                    "id": simulated_card_id,
                    "title": variables.get("input", {}).get("title", ""),
                    "createdAt": now,
                    "url": f"https://app.pipefy.com/pipes/000/cards/{simulated_card_id}",
                    "uuid": str(uuid.uuid4()),
                    "done": False,
                    "late": False,
                    "expired": False,
                    "due_date": None,
                    "started_current_phase_at": now,
                    "current_phase_age": 0,
                    "creatorEmail": "system@mundoinvest.com.br",
                    "emailMessagingAddress": None,
                    "inboxEmailsRead": 0,
                    "attachments_count": 0,
                    "comments_count": 0,
                    "checklist_items_count": 0,
                    "checklist_items_checked_count": 0,
                    "public_form_submitter_email": None,
                    "age": 0,
                    "overdue": False,
                    "finished_at": None,
                    "updated_at": now,
                    "path": f"pipes/000/cards/{simulated_card_id}",
                    "suid": f"SUID-{simulated_card_id}",
                }
            }
        }
    }


@_handle(UPDATE_CARD_FIELD_MUTATION)
def _mock_update_card_field_response(variables: dict) -> dict:
    """Gera resposta simulada para a mutation updateCardField (com aliasing)."""
    return {
        "data": {
            "updateStatus": {
                "clientMutationId": str(uuid.uuid4()),
                "success": True,
            },
            "updatePrioridade": {
                "clientMutationId": str(uuid.uuid4()),
                "success": True,
            },
        }
    }


# ---------------------------------------------------------------
# Ponto de entrada único — responsabilidade: logar e despachar
# ---------------------------------------------------------------


async def send_mutation(mutation: str, variables: dict) -> dict:
    """
    Simula o envio de uma mutation GraphQL ao Pipefy.

    Assinatura async para compatibilidade futura: em produção
    esta função fará HTTP POST via httpx.AsyncClient para a API
    GraphQL do Pipefy, operação de I/O que exige await.

    Args:
        mutation: String da mutation GraphQL (ex: CREATE_CARD_MUTATION).
        variables: Dicionário com as variáveis da mutation preenchidas pelo service.

    Returns:
        dict com a resposta simulada do Pipefy.
    """
    logger.info(
        "[PIPEFY MOCK] Mutation enviada ao Pipefy (simulação)\n"
        "  ── Mutation ──\n%s\n"
        "  ── Variáveis ──\n%s",
        mutation,
        variables,
    )

    handler = _MUTATION_HANDLERS.get(mutation)

    if handler is None:
        logger.warning(
            "[PIPEFY MOCK] Mutation não reconhecida. Retornando resposta genérica."
        )
        return {"data": None, "errors": [{"message": "Mock: mutation não reconhecida"}]}

    response = handler(variables)
    logger.info("[PIPEFY MOCK] Resposta simulada gerada com sucesso.")
    return response
