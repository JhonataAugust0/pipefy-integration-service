"""
Exceções de Domínio

Exceções de negócio sem dependência de frameworks HTTP.
Os routers (ou exception_handlers globais) as convertem em respostas 
HTTP adequadas (ex: 404, 409, 502).
"""

class ClienteNaoEncontradoError(Exception):
    """
    Disparada pelo WebhookService quando o cliente_email
    do payload não corresponde a nenhum registro no banco.

    O router captura esta exceção e retorna HTTP 404.
    """
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Cliente com e-mail '{email}' não encontrado.")


class EmailJaCadastradoError(Exception):
    """
    Disparada pelo ClienteService quando há tentativa de criar
    um cliente com um e-mail já existente na base.

    O router captura esta exceção e retorna HTTP 409.
    """
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"O e-mail '{email}' já está em uso por outro cliente.")


class PipefyIntegrationError(Exception):
    """
    Disparada por qualquer Service que dependa do Pipefy
    quando a API externa retorna erros GraphQL ou falha na comunicação.

    O router captura esta exceção e retorna HTTP 502.
    """
    def __init__(self, message: str, details: list | dict | None = None) -> None:
        self.details = details
        super().__init__(f"Falha na integração com o Pipefy: {message}")