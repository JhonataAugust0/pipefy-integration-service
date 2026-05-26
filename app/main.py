import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import setup_exception_handlers
from app.api.v1 import clientes, system, webhooks

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

    setup_exception_handlers(app)
    app.include_router(system.router)
    app.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
    app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

    logger.info("Mundo Invest Integration API inicializada com sucesso.")

    return app


app = create_app()
