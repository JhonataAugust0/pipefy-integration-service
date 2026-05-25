import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Application Factory: Isola a criação da instância do FastAPI.
    Facilita testes unitários (permite criar instâncias de teste limpas)
    e injeção de dependências futuras.
    """
    app = FastAPI(
        title="Mundo Invest — Pipefy Integration API",
        description="API de orquestração do funil de clientes da Mundo Invest. "
        "Gerencia a criação de perfis, cálculo de prioridade baseado em patrimônio "
        "e sincronização de status em tempo real via webhooks do Pipefy.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===================== Exception Handlers Globais =====================
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        Intercepta payloads malformados antes que cheguem na regra de negócio,
        garantindo log adequado e resposta limpa.
        """
        logger.warning(
            f"Payload malformado rejeitado em {request.url.path}: {exc.errors()}"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "Contrato de integração violado. Verifique o"
                "payload enviado.",
                "errors": exc.errors(),
            },
        )

    # ===================== Routers =====================
    from app.api.v1 import clientes, system

    app.include_router(system.router)
    app.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])

    logger.info("Mundo Invest Integration API inicializada com sucesso.")

    return app


app = create_app()
