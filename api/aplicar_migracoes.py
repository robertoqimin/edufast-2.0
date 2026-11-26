"""Aplicador revisado de migrations (A4). Por padrao SO MOSTRA O PLANO.

Uso, em api/ (o banco precisa ser informado explicitamente; o .env nunca e usado):

    EDUFAST_APPLY_DB_URL=postgresql+psycopg://... python aplicar_migracoes.py
    EDUFAST_APPLY_DB_URL=... python aplicar_migracoes.py --aplicar --confirmar NOME_DO_BANCO

- Banco vazio: cria pelo esquema base (base/esquema_vN.sql).
- Banco existente: aplica, em ordem, as propostas ausentes depois da versao estrutural.
- Recusa: proposta parcial, ordem quebrada, registro incompativel com a release, banco
  que nao seja PostgreSQL, ou outra aplicacao em andamento (trava no proprio banco).
- Cada proposta roda numa transacao junto com o registro da versao e o SHA-256 do arquivo:
  ou entra tudo, ou nada. Propostas anteriores a 008 sao registradas quando a 008 entra.
Executar somente depois da revisao do usuario e de backup de banco, uploads e chave.
"""
import argparse
import json
import os
import sys
import time

from schema_base import (arquivo_base, corpo_transacional, literal_registro, sql_checksum_base,
                         versao_base)
from schema_inventory import (AUSENTE, ESCOLA_DIR, checksum_arquivo, inventory, load_migrations,
                              parse_migration, problemas_registro, registry_rows, snapshot)

_DIVERGENCIA = 'Registro em educafast_migracoes difere'

TRAVA = 4542275  # chave da trava consultiva do PostgreSQL usada so por este aplicador
ENV_URL = 'EDUFAST_APPLY_DB_URL'


def _avisos(engine, tables, pendentes):
    from sqlalchemy import text
    avisos = []
    with engine.connect() as connection:
        if 'usuarios' in tables:
            mistos = connection.execute(text('SELECT count(*) FROM usuarios WHERE email <> lower(email)')).scalar()
            if mistos:
                avisos.append(f'{mistos} conta(s) com maiusculas no e-mail: o login compara em minusculas. '
                              'Revisar e normalizar esses e-mails antes de liberar o acesso.')
        if any(item['versao'] == 2 for item in pendentes) and 'usuarios' in tables:
            professores = connection.execute(text("SELECT count(*) FROM usuarios WHERE lower(tipo) = 'professor'")).scalar()
            if professores:
                avisos.append(f'A 002 coloca {professores} professor(es) em quarentena (estado pendente) ate '
                              'aprovacao administrativa. Revisar a lista de professores confiaveis antes.')
    return avisos


def planejar(engine, directory=ESCOLA_DIR, ate=None):
    """Plano somente leitura: o que seria feito, bloqueios e avisos (opcionalmente ate a versao 'ate')."""
    if engine.dialect.name != 'postgresql':
        return {'modo': 'recusado', 'bloqueios': ['O aplicador so opera bancos PostgreSQL.'], 'avisos': []}
    migrations = load_migrations(directory)
    atual = snapshot(engine)
    tabelas = atual['tables']
    if not tabelas:
        bloqueios = [] if ate is None else ['O esquema base cria a versao completa; --ate nao se aplica a banco vazio.']
        return {'modo': 'base', 'arquivo': arquivo_base(migrations), 'versao_final': versao_base(migrations),
                'pendentes': [], 'bloqueios': bloqueios, 'avisos': [], 'ate': ate}
    relatorio = inventory(engine, directory)
    registro_completo = 'checksum' in tabelas.get('educafast_migracoes', {}).get('columns', {})
    # Antes da 008 o registro e naturalmente incompleto; a propria 008 o preenche.
    bloqueios = [a for a in relatorio['alertas'] if registro_completo or not a.startswith(_DIVERGENCIA)]
    linhas = registry_rows(engine, tabelas) or []
    bloqueios += [p for p in problemas_registro(linhas, migrations, directory) if p not in bloqueios]
    estrutural = relatorio['versao_estrutural']
    por_versao = {item['versao']: item for item in relatorio['migrations']}
    pendentes = [{'versao': m['versao'], 'arquivo': m['arquivo']} for m in migrations
                 if m['versao'] > estrutural and (ate is None or m['versao'] <= ate)]
    for item in pendentes:
        situacao = por_versao[item['versao']]['situacao']
        if situacao != AUSENTE:
            bloqueios.append(f"{item['arquivo']} esta {situacao} apos a versao estrutural {estrutural}; revisar antes.")
    return {'modo': 'sequencial', 'versao_atual': estrutural, 'ate': ate,
            'versao_final': max((m['versao'] for m in migrations), default=0),
            'pendentes': pendentes, 'bloqueios': list(dict.fromkeys(bloqueios)),
            'avisos': _avisos(engine, tabelas, pendentes)}


def _sql_registro(itens):
    """Upsert das versoes aplicadas, com checksum, origem 'aplicada' e data de agora."""
    valores = ',\n'.join(
        f"    ({literal_registro(i['versao'], 'versao')}, {literal_registro(i['arquivo'][4:-4], 'descricao')}, "
        f"{literal_registro(i['arquivo'], 'arquivo')}, {literal_registro(i['checksum'], 'checksum')}, 'aplicada')"
        for i in itens)
    return ('INSERT INTO educafast_migracoes (versao, descricao, arquivo, checksum, origem) VALUES\n' + valores +
            '\nON CONFLICT (versao) DO UPDATE SET descricao = EXCLUDED.descricao, arquivo = EXCLUDED.arquivo, '
            "checksum = EXCLUDED.checksum, origem = 'aplicada', aplicada_em = CURRENT_TIMESTAMP;")


def aplicar(engine, plano, directory=ESCOLA_DIR, relogio=time.perf_counter):
    """Executa o plano. Retorna o tempo de cada passo. Recusa plano com bloqueios."""
    if plano['bloqueios']:
        raise RuntimeError('Plano com bloqueios; nada foi aplicado: ' + ' '.join(plano['bloqueios']))
    raw = engine.raw_connection()
    passos = []
    try:
        raw.driver_connection.autocommit = True
        with raw.driver_connection.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s)', (TRAVA,))
            if not cursor.fetchone()[0]:
                raise RuntimeError('Outra aplicacao de migrations esta em andamento neste banco; nada foi feito.')
            try:
                # O banco pode ter mudado entre o plano mostrado e a trava: replanejar sob a trava.
                atual = planejar(engine, directory, plano.get('ate'))
                if (atual['modo'], atual.get('pendentes'), atual['bloqueios']) != (
                        plano['modo'], plano.get('pendentes'), plano['bloqueios']):
                    raise RuntimeError('O banco mudou desde o plano; revise o novo plano. Nada foi aplicado.')
                if plano['modo'] == 'base':
                    caminho = directory / plano['arquivo']
                    inicio = relogio()
                    corpo = corpo_transacional(caminho.read_text(encoding='utf-8'))
                    sql = f"BEGIN;\n{corpo}\n{sql_checksum_base(plano['arquivo'], checksum_arquivo(caminho))}\nCOMMIT;"
                    _executar(cursor, sql)
                    passos.append({'arquivo': plano['arquivo'], 'segundos': round(relogio() - inicio, 3)})
                    return passos
                cursor.execute("SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
                               "AND table_name = 'educafast_migracoes' AND column_name = 'checksum'")
                registro_completo = cursor.fetchone() is not None
                sem_registro = []
                for item in plano['pendentes']:
                    caminho = directory / item['arquivo']
                    atual = {**item, 'checksum': checksum_arquivo(caminho)}
                    corpo = corpo_transacional(caminho.read_text(encoding='utf-8'))
                    cria_checksum = ('educafast_migracoes', 'checksum') in parse_migration(corpo)['columns']
                    completa_registro = registro_completo or cria_checksum
                    registro = _sql_registro(sem_registro + [atual]) if completa_registro else ''
                    inicio = relogio()
                    _executar(cursor, f'BEGIN;\n{corpo}\n{registro}\nCOMMIT;')
                    passos.append({'arquivo': item['arquivo'], 'segundos': round(relogio() - inicio, 3)})
                    if completa_registro:
                        registro_completo, sem_registro = True, []
                    else:
                        sem_registro.append(atual)
                return passos
            finally:
                cursor.execute('SELECT pg_advisory_unlock(%s)', (TRAVA,))
    finally:
        raw.driver_connection.autocommit = False
        raw.close()


def _executar(cursor, sql):
    try:
        cursor.execute(sql)
    except Exception:
        cursor.execute('ROLLBACK')
        raise


def _imprimir(plano):
    if plano['modo'] == 'base':
        print(f"Banco vazio: criar pelo esquema base {plano['arquivo']} (versao {plano['versao_final']}).")
    elif plano['modo'] == 'sequencial':
        print(f"Versao estrutural atual: {plano['versao_atual']}; ultima da release: {plano['versao_final']}.")
        for item in plano['pendentes']:
            print(f"  aplicar {item['arquivo']}")
        if not plano['pendentes']:
            print('  nada a aplicar.')
    for aviso in plano['avisos']:
        print('AVISO: ' + aviso)
    for bloqueio in plano['bloqueios']:
        print('BLOQUEIO: ' + bloqueio)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Aplicador revisado de migrations (padrao: somente plano).')
    parser.add_argument('--aplicar', action='store_true', help='Executa o plano (exige --confirmar).')
    parser.add_argument('--confirmar', help='Nome exato do banco alvo, para confirmar a aplicacao.')
    parser.add_argument('--ate', type=int, help='Aplica somente ate esta versao (atualizacao em etapas).')
    parser.add_argument('--json', action='store_true', help='Saida em JSON.')
    args = parser.parse_args(argv)
    url = os.environ.get(ENV_URL)
    if not url:
        raise SystemExit(f'Defina {ENV_URL} explicitamente; o .env nao e usado como destino.')
    from sqlalchemy import create_engine
    engine = create_engine(url)
    try:
        plano = planejar(engine, ate=args.ate)
        resultado = {'plano': plano}
        if args.aplicar:
            if args.confirmar != engine.url.database:
                raise SystemExit('Confirme com --confirmar e o nome exato do banco alvo; nada foi aplicado.')
            resultado['passos'] = aplicar(engine, plano)
            depois = inventory(engine)
            resultado['depois'] = {'versao_estrutural': depois['versao_estrutural'], 'alertas': depois['alertas']}
        if args.json:
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        else:
            _imprimir(plano)
            for passo in resultado.get('passos', []):
                print(f"aplicado {passo['arquivo']} em {passo['segundos']} s")
            if 'depois' in resultado:
                print(f"Depois: versao estrutural {resultado['depois']['versao_estrutural']}; "
                      f"alertas: {resultado['depois']['alertas'] or 'nenhum'}")
        bloqueado = bool(plano['bloqueios']) or bool(resultado.get('depois', {}).get('alertas'))
        return 1 if bloqueado else 0
    finally:
        engine.dispose()


if __name__ == '__main__':
    sys.exit(main())
