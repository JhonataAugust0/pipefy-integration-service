import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_database_connection(db_session: AsyncSession):
    """
    Testa a conexão com o banco de dados executando uma consulta simples (SELECT 1),
    validando se a fixture 'db_session' consegue se comunicar com o banco de testes.
    """
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar()

    assert value == 1
