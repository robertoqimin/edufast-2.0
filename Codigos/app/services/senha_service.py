"""Regra de senha (S4), num lugar so.

Todas as contas: pelo menos 12 caracteres e um caractere especial (decisao do usuario em
24/11/2026, substituindo o minimo de 6 para aluno/professor definido em 23/11/2026).
Limite maximo evita que uma senha enorme consuma CPU no calculo do hash.
"""
MINIMO = 12
MINIMO_ADMIN = MINIMO  # mesma regra para todos os perfis
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
