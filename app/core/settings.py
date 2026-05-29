"""
Configuração centralizada da aplicação.

Todas as variáveis de ambiente são lidas, tipadas e validadas aqui.

Usa ``pydantic_settings.BaseSettings`` para:
  • Leitura automática do ``.env``
  • Conversão e validação de tipos (fail-fast no startup)
  • Documentação via ``Field(description=...)``
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Schema único para todas as variáveis de ambiente da aplicação.

    Se uma variável obrigatória estiver ausente, o Pydantic derruba
    o startup imediatamente com mensagem clara (fail-fast).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Banco de Dados -----------------------------------------------
    DATABASE_URL: str = Field(
        description="Connection string do banco principal (async).",
    )

    TEST_DATABASE_URL: str | None = Field(
        default=None,
        description=(
            "Connection string do banco de testes. "
            "Obrigatória apenas em ambiente de testes."
        ),
    )

    # --- Pipefy -------------------------------------------------------
    PIPEFY_PIPE_ID: str = Field(
        default="000000",
        description="ID do Pipe no Pipefy.",
    )
    PIPEFY_PHASE_ID: str = Field(
        default="000000",
        description="ID da Phase inicial no Pipefy.",
    )
    PIPEFY_API_TOKEN: str = Field(
        default="mock_token",
        description="Token de autenticação da API do Pipefy.",
    )

    # --- Aplicação ----------------------------------------------------
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ],
        description="Lista de origens permitidas no CORS.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description=(
            "Nível de log "
            "(DEBUG, INFO, WARNING, ERROR, CRITICAL)."
        ),
    )
    ENV: str = Field(
        default="development",
        description=(
            "Ambiente de execução "
            "(development, staging, production)."
        ),
    )
    APPLICATION_PORT: int = Field(
        default=8000,
        description="Porta da aplicação.",
    )
    WORKERS: int = Field(
        default=1,
        description="Número de workers Uvicorn.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Singleton cacheado de ``Settings``.

    Em testes, limpar o cache com ``get_settings.cache_clear()`` para
    permitir que variáveis de ambiente de teste sejam relidas.
    """
    return Settings()
