"""Ensaio de atualizacao (A4): legado com dados -> backup -> 001..N -> app -> volta atras.

Tudo em containers e volumes descartaveis deste projeto; nao aceita banco externo.
Evidencias: .ci-results/ensaio-atualizacao/<projeto>/summary.json (tempos e verificacoes).
Uso, na raiz: python .github/cicd/run_ensaio_atualizacao.py [--image edufast-platform:test]
"""
import argparse
import base64
import hashlib
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_cursos_backend import POSTGRES_APP_ROLE  # noqa: E402  mesmo papel sem superusuario

BANCO, USUARIO = 'edufast_ensaio', 'ensaio'
SENHA_CONTAS = 'Ensaio-legado-2026!'


class Ensaio:
    def __init__(self, image):
        self.project = 'edufast-ensaio-' + uuid4().hex[:10]
        self.report = ROOT / '.ci-results' / 'ensaio-atualizacao' / self.project
        self.report.mkdir(parents=True)
        self.temp = Path(tempfile.mkdtemp(prefix=self.project + '-'))
        self.summary = {'passed': False, 'project': self.project, 'image': image, 'passos': [], 'verificacoes': {}}
        db_password = uuid4().hex
        url = f'postgresql+psycopg://{USUARIO}:{db_password}@db-ensaio:5432/{BANCO}'
        common = {'image': image, 'working_dir': '/repo/Codigos',
                  'volumes': [{'type': 'bind', 'source': str(ROOT), 'target': '/repo', 'read_only': True},
                              'uploads:/app/uploads'],
                  'environment': {'DB_URL': url, 'EDUFAST_APPLY_DB_URL': url, 'EDUFAST_ENSAIO': '1',
                                  'APP_ENV': 'development', 'PYTHON_DOTENV_DISABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                                  'SECRET_KEY': 'synthetic-ensaio-only-secret-key-2026-32chars',
                                  'DATA_ENCRYPTION_KEY': base64.urlsafe_b64encode(os.urandom(32)).decode(),
                                  'UPLOAD_FOLDER': '/app/uploads',
                                  'PYTHONPATH': '/repo/Codigos:/repo/.github/cicd/tests'}}
        self.key_sha = hashlib.sha256(common['environment']['DATA_ENCRYPTION_KEY'].encode()).hexdigest()
        compose = {'services': {
            'db-ensaio': {'image': 'postgres:17-alpine', 'networks': ['isolated'], 'tmpfs': ['/var/lib/postgresql/data'],
                          'environment': {'POSTGRES_DB': BANCO, 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': uuid4().hex,
                                          'APP_DB_USER': USUARIO, 'APP_DB_PASSWORD': db_password},
                          'configs': [{'source': 'postgres-app-role', 'target': '/docker-entrypoint-initdb.d/10-app-role.sh'}],
                          'healthcheck': {'test': ['CMD-SHELL', 'PGPASSWORD="$$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$$APP_DB_USER" '
                                                   '-d "$$POSTGRES_DB" -tAc "SELECT 1" >/dev/null'],
                                          'interval': '2s', 'timeout': '3s', 'retries': 60}},
            'tools': {**common, 'networks': ['isolated'], 'entrypoint': ['python']},
            'app': {**common, 'networks': ['isolated', 'web'], 'ports': ['127.0.0.1::8000'],
                    'entrypoint': ['gunicorn', '-b', '0.0.0.0:8000', '--workers', '1', 'app:create_app()']},
        }, 'networks': {'isolated': {'internal': True}, 'web': {}}, 'volumes': {'uploads': {}},
            'configs': {'postgres-app-role': {'content': POSTGRES_APP_ROLE.replace('$', '$$')}}}
        config = self.temp / 'compose.json'
        config.write_text(json.dumps(compose), encoding='utf-8')
        self.base = ['docker', 'compose', '-p', self.project, '-f', str(config)]

    def run(self, nome, args, stdin=None, binary=False):
        result = subprocess.run(self.base + args, cwd=ROOT, input=stdin, capture_output=True, timeout=900)
        (self.report / f'{nome}.log').write_bytes(result.stdout + b'\n--- stderr ---\n' + result.stderr)
        if result.returncode:
            raise RuntimeError(f'{nome} falhou; consulte {self.report}')
        return result.stdout if binary else result.stdout.decode('utf-8', errors='replace')

    def passo(self, nome, funcao):
        inicio = time.perf_counter()
        valor = funcao()
        segundos = round(time.perf_counter() - inicio, 2)
        self.summary['passos'].append({'passo': nome, 'segundos': segundos})
        print(f'{nome}: ok ({segundos} s)', flush=True)
        return valor

    def etapa(self, nome):
        saida = self.run(nome, ['run', '--rm', '--no-deps', '-T', 'tools', '/repo/.github/cicd/ensaio_etapas.py', nome])
        return json.loads(re.search(r'^RESULTADO (.*)$', saida, re.M).group(1))

    def aplicador(self, nome, *extra):
        saida = self.run(nome, ['run', '--rm', '--no-deps', '-T', 'tools', 'aplicar_migracoes.py', '--json', *extra])
        return json.loads(saida[saida.index('{'):])

    def psql_admin(self, nome, sql):
        return self.run(nome, ['exec', '-T', 'db-ensaio', 'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', 'postgres', '-c', sql])

    def http(self, porta, documento, documento_sha):
        alvo = f'http://127.0.0.1:{porta}'
        for _ in range(100):
            try:
                with urllib.request.urlopen(alvo + '/healthz', timeout=2) as resposta:
                    if resposta.status == 200:
                        break
            except OSError:
                time.sleep(0.3)
        else:
            raise RuntimeError('Aplicacao nao respondeu /healthz')

        def login(email):
            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
            pedido = urllib.request.Request(alvo + '/login', data=json.dumps({'email': email, 'senha': SENHA_CONTAS}).encode(),
                                            headers={'Content-Type': 'application/json'})
            try:
                with opener.open(pedido, timeout=10) as resposta:
                    return resposta.status, opener
            except urllib.error.HTTPError as erro:
                return erro.code, opener

        resultados = {'healthz': 200}
        resultados['login_admin'], _ = login('admin@legado.test')
        resultados['login_aluna'], aluna = login('aluna@legado.test')
        with aluna.open(alvo + f'/arquivos/download/{documento}', timeout=10) as resposta:
            resultados['download_aluna_identico'] = hashlib.sha256(resposta.read()).hexdigest() == documento_sha
        resultados['login_professor_em_quarentena'], _ = login('professor@legado.test')
        resultados['login_email_com_maiusculas_legado'], _ = login('Misto@Legado.test')
        esperado = {'healthz': 200, 'login_admin': 200, 'login_aluna': 200, 'download_aluna_identico': True,
                    'login_professor_em_quarentena': 403, 'login_email_com_maiusculas_legado': 401}
        if resultados != esperado:
            raise RuntimeError(f'HTTP diferente do esperado: {resultados}')
        return resultados

    def executar(self):
        v = self.summary['verificacoes']
        self.passo('banco-pronto', lambda: self.run('db-up', ['up', '-d', '--wait', '--wait-timeout', '180', 'db-ensaio']))
        legado = self.passo('legado-com-dados', lambda: self.etapa('legado'))
        antes = self.passo('retrato-antes', lambda: self.etapa('retrato'))
        v['antes'] = {'versao_estrutural': antes['versao_estrutural'], 'tabelas': antes['tabelas']}
        dump = self.passo('backup-banco', lambda: self.run('backup-banco', [
            'exec', '-T', 'db-ensaio', 'sh', '-c', 'PGPASSWORD="$APP_DB_PASSWORD" exec pg_dump -h 127.0.0.1 -U "$APP_DB_USER" '
            '-d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges'], binary=True))
        uploads = self.passo('backup-uploads', lambda: self.run('backup-uploads', [
            'run', '--rm', '--no-deps', '-T', '--entrypoint', 'tar', 'tools', '-C', '/app/uploads', '-czf', '-', '.'], binary=True))
        v['backup'] = {'banco_bytes': len(dump), 'uploads_bytes': len(uploads), 'chave_sha256': self.key_sha}
        plano = self.passo('plano', lambda: self.aplicador('plano'))['plano']
        v['plano'] = {'pendentes': [p['arquivo'] for p in plano['pendentes']], 'bloqueios': plano['bloqueios'],
                      'avisos': plano['avisos']}
        aplicado = self.passo('aplicar', lambda: self.aplicador('aplicar', '--aplicar', '--confirmar', BANCO))
        v['aplicacao'] = {'passos': aplicado['passos'], 'depois': aplicado['depois']}
        depois = self.passo('retrato-depois', lambda: self.etapa('retrato'))
        v['dados_preservados'] = depois['dados'] == antes['dados']
        v['depois'] = {'versao_estrutural': depois['versao_estrutural'], 'alertas': depois['alertas'], 'tabelas': depois['tabelas']}
        v['producao'] = self.passo('inicializacao-producao', lambda: self.etapa('producao'))
        self.passo('app-pronta', lambda: self.run('app-up', ['up', '-d', 'app']))
        porta = int(self.run('app-port', ['port', 'app', '8000']).strip().rsplit(':', 1)[1])
        v['http'] = self.passo('http-sobre-banco-atualizado', lambda: self.http(porta, legado['documento'], legado['sha256']))
        self.passo('parar-app', lambda: self.run('app-stop', ['stop', 'app']))
        # Volta atras: banco recriado vazio e restaurado do backup (procedimento de recuperacao).
        self.passo('recriar-banco-vazio', lambda: (
            self.psql_admin('drop-db', f'DROP DATABASE {BANCO} WITH (FORCE)'),
            self.psql_admin('create-db', f'CREATE DATABASE {BANCO} OWNER {USUARIO}')))
        self.passo('restaurar-banco', lambda: self.run('restaurar-banco', [
            'exec', '-T', 'db-ensaio', 'sh', '-c', 'PGPASSWORD="$APP_DB_PASSWORD" psql -v ON_ERROR_STOP=1 -q --single-transaction '
            '-h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB"'], stdin=dump))
        self.passo('restaurar-uploads', lambda: self.run('restaurar-uploads', [
            'run', '--rm', '--no-deps', '-T', '--entrypoint', 'sh', 'tools', '-c',
            'rm -rf /app/uploads/* && tar -C /app/uploads -xzf -'], stdin=uploads))
        restaurado = self.passo('retrato-restaurado', lambda: self.etapa('retrato'))
        v['volta_atras'] = {'dados_iguais_ao_antes': restaurado['dados'] == antes['dados'],
                            'versao_estrutural': restaurado['versao_estrutural'], 'tabelas': restaurado['tabelas']}
        conferido = self.run('uploads-conferidos', ['run', '--rm', '--no-deps', '-T', '--entrypoint', 'sha256sum', 'tools',
                                                      '/app/uploads/' + legado['documento']])
        v['volta_atras']['documento_identico'] = conferido.split()[0] == legado['sha256']
        ok = (v['dados_preservados'] and not plano['bloqueios'] and not v['depois']['alertas']
              and v['depois']['versao_estrutural'] == plano['versao_final'] and v['volta_atras']['dados_iguais_ao_antes']
              and v['volta_atras']['versao_estrutural'] == antes['versao_estrutural']
              and v['volta_atras']['tabelas'] == antes['tabelas'] and v['volta_atras']['documento_identico'])
        if not ok:
            raise RuntimeError('Verificacoes do ensaio nao conferem; ver summary.json')
        self.summary['passed'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='edufast-platform:test')
    args = parser.parse_args()
    if not re.fullmatch(r'edufast-(?:platform:test|ci-[a-f0-9]{10}:tested)', args.image):
        parser.error('Use somente imagem local de teste EduFast.')
    ensaio = Ensaio(args.image)
    try:
        ensaio.executar()
    except Exception as erro:
        ensaio.summary['erro'] = str(erro)
        print('FALHA: ' + str(erro), flush=True)
    finally:
        limpeza = subprocess.run(ensaio.base + ['down', '-v', '--remove-orphans'], cwd=ROOT, capture_output=True, timeout=120)
        ensaio.summary['limpeza_ok'] = limpeza.returncode == 0
        ensaio.summary['passed'] = ensaio.summary['passed'] and ensaio.summary['limpeza_ok']
        (ensaio.report / 'summary.json').write_text(json.dumps(ensaio.summary, indent=2, ensure_ascii=False), encoding='utf-8')
        print('Evidencias: ' + str(ensaio.report))
    return 0 if ensaio.summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
