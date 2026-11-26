"""Limites explícitos: configurações inválidas impedem iniciar o processo."""
import os


def bounded_int(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} deve ser inteiro") from None
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} fora do intervalo {minimum}..{maximum}")
    return value
