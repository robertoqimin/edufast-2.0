"""Regra de senha (S4), num lugar so.

Contas de aluno e professor: pelo menos 6 caracteres e um caractere especial (decisao do
usuario em 23/11/2026). Contas administrativas mantem 12 caracteres, tambem com especial.
Limite maximo evita que uma senha enorme consuma CPU no calculo do hash.
"""
MINIMO = 6
MINIMO_ADMIN = 12
MAXIMO = 128


def problema_senha(senha, minimo=MINIMO):
    """Mensagem para o usuario quando a senha nao serve; None quando serve."""
    if not isinstance(senha, str) or len(senha) < minimo:
        return f'A senha deve ter pelo menos {minimo} caracteres e um caractere especial (ex.: ! @ # - _).'
    if len(senha) > MAXIMO:
        return f'A senha deve ter no maximo {MAXIMO} caracteres.'
    if not any(not c.isalnum() and not c.isspace() for c in senha):
        return f'A senha deve ter pelo menos {minimo} caracteres e um caractere especial (ex.: ! @ # - _).'
    return None
