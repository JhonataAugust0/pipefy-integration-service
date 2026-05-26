"""
Testes unitários — calculate_priority

Função pura: sem banco, sem HTTP, sem fixtures.
Cada teste verifica um ponto da especificação RF-08.
"""

import pytest

from app.domain.priority import (
    HIGH_PRIORITY,
    HIGH_PRIORITY_THRESHOLD,
    NORMAL_PRIORITY,
    calculate_priority,
)


class TestCalculatePriority:
    """Testes de calculate_priority agrupados por categoria de boundary."""

    # ── Casos exigidos pelo desafio ───────────────────────────────────────────

    def test_patrimonio_acima_threshold_retorna_prioridade_alta(self):
        """RF-08: patrimônio > 200_000 → prioridade_alta."""
        assert calculate_priority(250_000) == HIGH_PRIORITY

    def test_patrimonio_abaixo_threshold_retorna_prioridade_normal(self):
        """RF-08: patrimônio < 200_000 → prioridade_normal."""
        assert calculate_priority(150_000) == NORMAL_PRIORITY

    # ── Boundary condition: exatamente no threshold ────────────────────────────

    def test_patrimonio_exatamente_no_threshold_retorna_prioridade_alta(self):
        """
        RF-08 usa '>=' — 200_000 exato deve retornar prioridade_alta.
        Testa o boundary condition crítico da especificação.
        """
        assert calculate_priority(HIGH_PRIORITY_THRESHOLD) == HIGH_PRIORITY

    def test_patrimonio_um_centavo_abaixo_do_threshold_retorna_prioridade_normal(self):
        """200_000 - 0.01 deve retornar prioridade_normal (abaixo do threshold)."""
        assert calculate_priority(HIGH_PRIORITY_THRESHOLD - 0.01) == NORMAL_PRIORITY

    # ── Casos extremos ─────────────────────────────────────────────────────────

    def test_patrimonio_zero_retorna_prioridade_normal(self):
        """Patrimônio zero — edge case defensivo."""
        assert calculate_priority(0.0) == NORMAL_PRIORITY

    def test_patrimonio_muito_alto_retorna_prioridade_alta(self):
        """Patrimônio muito elevado não deve quebrar a lógica."""
        assert calculate_priority(50_000_000) == HIGH_PRIORITY

    # ── Cobertura parametrizada ao redor do threshold ──────────────────────────

    @pytest.mark.parametrize(
        "valor,esperado",
        [
            (199_999.99, NORMAL_PRIORITY),
            (200_000.00, HIGH_PRIORITY),
            (200_000.01, HIGH_PRIORITY),
        ],
    )
    def test_valores_parametrizados_ao_redor_do_threshold(self, valor, esperado):
        """Cobertura parametrizada dos pontos críticos do threshold."""
        assert calculate_priority(valor) == esperado
