"""initial schema: clientes and processed_events

Create Date: 2026-05-25

"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Tabela: clientes
    # ------------------------------------------------------------------
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cliente_nome", sa.String(255), nullable=False),
        sa.Column("cliente_email", sa.String(255), nullable=False),
        sa.Column("tipo_solicitacao", sa.String(255), nullable=False),
        sa.Column("valor_patrimonio", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="Aguardando Análise",
        ),
        sa.Column("prioridade", sa.String(50), nullable=True),
        # id do card retornado pela mutation createCard do Pipefy.
        # Nulo até createCard ser executado com sucesso.
        sa.Column("pipefy_card_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_clientes_cliente_email", "clientes", ["cliente_email"], unique=True
    )

    # ------------------------------------------------------------------
    # Tabela: processed_events
    # Constraint UNIQUE em event_id suporta INSERT ON CONFLICT DO NOTHING
    # para controle de idempotência transacional de webhooks.
    # ------------------------------------------------------------------
    op.create_table(
        "processed_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_processed_events_event_id"),
    )
    op.create_index(
        "ix_processed_events_event_id", "processed_events", ["event_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_processed_events_event_id", table_name="processed_events")
    op.drop_table("processed_events")
    op.drop_index("ix_clientes_cliente_email", table_name="clientes")
    op.drop_table("clientes")
