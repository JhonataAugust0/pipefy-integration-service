"""
Schemas Pydantic — Cliente

Contratos de entrada e saída da API para o recurso Cliente.
O Pydantic valida automaticamente os campos na camada HTTP,
rejeitando payloads malformados.
"""

from pydantic import BaseModel, EmailStr, Field


class ClienteCreate(BaseModel):
    """
    Schema de entrada para POST /clientes.

    Campos obrigatórios conforme RF-02:
      - cliente_nome: nome do cliente
      - cliente_email: e-mail válido (validado pelo EmailStr)
      - tipo_solicitacao: tipo de solicitação
      - valor_patrimonio: valor do patrimônio (float positivo)
    """

    cliente_nome: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nome completo do cliente",
        examples=["João Silva"],
    )
    cliente_email: EmailStr = Field(
        ...,
        description="E-mail válido do cliente",
        examples=["joao.silva@example.com"],
    )
    tipo_solicitacao: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Tipo da solicitação do cliente",
        examples=["Atualização cadastral"],
    )
    valor_patrimonio: float = Field(
        ...,
        gt=0,
        description="Valor do patrimônio do cliente em reais",
        examples=[250000.00],
    )


class ClienteResponse(BaseModel):
    """
    Schema de saída para POST /clientes (HTTP 201).

    Reflete os campos persistidos no banco + indicador da mutation enviada,
    conforme o exemplo de resposta da seção 6 do README.
    """

    id: int
    cliente_nome: str
    cliente_email: str
    status: str
    pipefy_mutation_sent: str = Field(
        description="Nome da mutation GraphQL estruturada para o Pipefy",
        examples=["createCard"],
    )

    model_config = {"from_attributes": True}
