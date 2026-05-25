"""
Router — Sistema (GET /health)

Endpoints de infraestrutura, probes e telemetria.
"""

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check(response: Response, db: AsyncSession = Depends(get_session)):
    """Deep Health Check (Readiness Probe)."""
    health_status = {
        "status": "healthy",
        "service": "pipefy-integration-api",
        "dependencies": {"database": "unknown"},
    }

    try:
        await db.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = "healthy"

    except Exception as e:
        logger.error(f"[HEALTHCHECK] Falha na conexão: {str(e)}")
        health_status["status"] = "unhealthy"
        health_status["dependencies"]["database"] = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status
