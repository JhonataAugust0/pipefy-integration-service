"""
Modelo SQLAlchemy — ProcessedEvent

Armazena event_ids de webhooks já processados. Utilizada pelo
webhook_service para evitar reprocessamento de eventos duplicados
enviados pelo Pipefy (INSERT ON CONFLICT DO NOTHING).
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.session import Base


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessedEvent(event_id='{self.event_id}', "
            f"processed_at='{self.processed_at}')>"
        )
