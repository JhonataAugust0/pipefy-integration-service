"""
Mapeamento Global de Exceções (Exception Handlers)

Converte exceções de domínio (puras) e erros de validação (Pydantic)
em respostas HTTP padronizadas (JSONResponse) para o cliente.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    ClienteNaoEncontradoError,
    EmailJaCadastradoError,
    PipefyIntegrationError,
)

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Registra os manipuladores de exceção na instância da aplicação FastAPI."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warning(
            f"Payload malformado rejeitado em {request.url.path}: {exc.errors()}"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "message": "Contrato de integração violado. Verifique o payload "
                "enviado.",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(ClienteNaoEncontradoError)
    async def cliente_nao_encontrado_handler(
        request: Request, exc: ClienteNaoEncontradoError
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(EmailJaCadastradoError)
    async def email_ja_cadastrado_handler(
        request: Request, exc: EmailJaCadastradoError
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PipefyIntegrationError)
    async def pipefy_integration_handler(request: Request, exc: PipefyIntegrationError):
        logger.error(f"Falha de integração Pipefy detectada: {exc.details}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc), "provider_errors": exc.details},
        )
