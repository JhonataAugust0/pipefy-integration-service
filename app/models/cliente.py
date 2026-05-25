"""
Modelo SQLAlchemy — Cliente

Representa o cliente cadastrado no sistema. Campos mapeados conforme
a seção 2.3 do README (Etapa 1 · Modelagem):
  - cliente_nome, cliente_email, tipo_solicitacao, valor_patrimonio
  - status (default: "Aguardando Análise")
  - prioridade (preenchido após processamento do webhook)
  - pipefy_card_id (preenchido com o ID retornado pelo createCard mock)
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    cliente_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cliente_email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    tipo_solicitacao: Mapped[str] = mapped_column(String(255), nullable=False)
    valor_patrimonio: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Aguardando Análise"
    )
    prioridade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pipefy_card_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Cliente(id={self.id}, nome='{self.cliente_nome}', "
            f"email='{self.cliente_email}', status='{self.status}')>"
        )
