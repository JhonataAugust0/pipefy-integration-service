"""
Regra de Prioridade

Regra (RF-08):
  valor_patrimonio >= 200_000 → "prioridade_alta"
  valor_patrimonio <  200_000 → "prioridade_normal"
"""

HIGH_PRIORITY_THRESHOLD: float = 200_000.0
HIGH_PRIORITY: str = "prioridade_alta"
NORMAL_PRIORITY: str = "prioridade_normal"


def calculate_priority(asset_value: float) -> str:
    """
    Calcula a prioridade de atendimento de um cliente com base no patrimônio.

    Args:
        asset_value: Valor do patrimônio do cliente em reais.

    Returns:
        "prioridade_alta"   se asset_value >= 200_000
        "prioridade_normal" se asset_value <  200_000
    """
    return HIGH_PRIORITY if asset_value >= HIGH_PRIORITY_THRESHOLD else NORMAL_PRIORITY
