# Stage 1 — builder
# Instala dependências de build.
# O resultado (/install) é copiado para os stages seguintes,
# mantendo a imagem final livre de ferramentas de compilação.
# =============================================================================
FROM python:3.14-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# =============================================================================
# Stage 2 — development
# Inclui dependências de dev e roda com --reload.
# =============================================================================
FROM python:3.14-slim AS development

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pacotes de produção
COPY --from=builder /install /usr/local

# Instala dependências de dev separadamente (não entram no stage production)
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# =============================================================================
# Stage 3 — production
# Imagem mínima: sem gcc, sem curl, sem dev deps, sem código de teste.
# Roda como usuário não-root (appuser).
# =============================================================================
FROM python:3.14-slim AS production

WORKDIR /app

# Apenas runtime lib do PostgreSQL (libpq5)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Pacotes instalados no builder
COPY --from=builder /install /usr/local

# Apenas o código da aplicação e configuração de migração
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Usuário não-root: reduz superfície de ataque em caso de RCE
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --no-create-home appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-1}"]
