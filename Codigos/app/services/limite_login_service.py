"""Limite de tentativas de login (S1): por conta e por IP, sem guardar e-mail nem IP.

- Conta: ``LOGIN_MAX_TENTATIVAS`` (5) falhas seguidas bloqueiam por ``LOGIN_BLOQUEIO_MINUTOS`` (15).
- IP: limite maior (``LOGIN_MAX_TENTATIVAS_IP``, 30), porque uma escola inteira costuma
  sair pelo mesmo IP; serve para conter quem testa muitas contas.
- E-mails inexistentes contam como os existentes: o bloqueio nao revela se a conta existe.
- A chave gravada e um HMAC-SHA256 com a SECRET_KEY: uma copia do banco nao permite
  descobrir e-mails ou IPs testando listas.
- A contagem e atomica (INSERT ... ON CONFLICT DO UPDATE), sem corrida entre tentativas.
"""
import hashlib
import hmac
import time

from flask import current_app, request
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models import LimiteLoginModel

_TABELA = LimiteLoginModel.__table__


def _chave(tipo, valor):
    segredo = current_app.config['SECRET_KEY'].encode('utf-8')
    return hmac.new(segredo, f'{tipo}:{valor}'.encode('utf-8'), hashlib.sha256).hexdigest()


def _minuto_atual():
    return int(time.time() // 60)


def _limites():
    config = current_app.config
    return config['LOGIN_MAX_TENTATIVAS'], config['LOGIN_MAX_TENTATIVAS_IP'], config['LOGIN_BLOQUEIO_MINUTOS']


def chaves(email):
    return {_chave('conta', email): 'conta', _chave('ip', request.remote_addr or ''): 'ip'}


def minutos_bloqueado(db, email):
    """0 quando pode tentar; senao, minutos restantes do bloqueio mais longo."""
    max_conta, max_ip, bloqueio = _limites()
    agora = _minuto_atual()
    alvos = chaves(email)
    restante = 0
    for linha in db.execute(select(_TABELA).where(_TABELA.c.chave.in_(list(alvos)))).mappings():
        limite = max_conta if alvos[linha['chave']] == 'conta' else max_ip
        if linha['tentativas'] >= limite and linha['janela'] > agora - bloqueio:
            restante = max(restante, linha['janela'] + bloqueio - agora)
    return restante


def registrar_falha(db, email):
    """Soma uma falha para a conta e para o IP; reinicia a contagem apos a janela."""
    _, _, bloqueio = _limites()
    agora = _minuto_atual()
    construtor = {'postgresql': postgresql_insert, 'sqlite': sqlite_insert}[db.bind.dialect.name]
    for chave in chaves(email):
        comando = construtor(_TABELA).values(chave=chave, janela=agora, tentativas=1)
        comando = comando.on_conflict_do_update(index_elements=['chave'], set_={
            'tentativas': case((_TABELA.c.janela <= agora - bloqueio, 1), else_=_TABELA.c.tentativas + 1),
            'janela': agora,
        })
        db.execute(comando)
    # Linhas vencidas nao bloqueiam mais ninguem: limpeza pelo indice de janela, sem crescer sem fim.
    db.execute(delete(_TABELA).where(_TABELA.c.janela <= agora - bloqueio))


def limpar_conta(db, email):
    """Senha correta zera a contagem da conta (a do IP segue a janela)."""
    db.execute(delete(_TABELA).where(_TABELA.c.chave == _chave('conta', email)))
