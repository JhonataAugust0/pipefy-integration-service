"""
Router — Clientes (POST /clientes)

Camada de transporte HTTP para o recurso Cliente.
Recebe requisição, valida via schema e delega ao
service injetado via Depends().
"""

import logging

from fastapi import APIRouter, Depends, status

from app.api.deps import get_cliente_service
from app.schemas.cliente import ClienteCreate, ClienteResponse
from app.services.cliente_service import ClienteService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra novo cliente",
    description=(
        "Cria um novo cliente no sistema, persiste no banco com status "
        "'Aguardando Análise' e estrutura a mutation GraphQL createCard "
        "para o Pipefy."
    ),
)
async def post_clientes(
    payload: ClienteCreate,
    service: ClienteService = Depends(get_cliente_service),
) -> ClienteResponse:
    """
    Endpoint RF-01 / RF-02 / RF-03 / RF-04.

    Fluxo:
      1. Pydantic valida o payload (campos obrigatórios + formato de e-mail)
      2. Service persiste o cliente e envia mutation ao Pipefy (mock)
      3. Retorna o cliente criado com indicador da mutation enviada
    """
    cliente = await service.create_cliente(payload=payload)

    return ClienteResponse(
        id=cliente.id,
        cliente_nome=cliente.cliente_nome,
        cliente_email=cliente.cliente_email,
        status=cliente.status,
        pipefy_mutation_sent="createCard",
    )
