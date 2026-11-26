"""B3/MS05: mede as jornadas por perfil em containers com orçamento fixo (2 vCPU, 2 GB).

Banco PostgreSQL 17 descartável (tmpfs) com 0,5 vCPU e 512 MiB; aplicação com 1,5 vCPU e
1,5 GiB, a partir da imagem de teste. Repositório montado só para leitura; relatório em
.ci-results/desempenho/<execucao>. Nada persiste depois da execução.
"""
import argparse
import json
import os
import base64
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_cursos_backend import POSTGRES_APP_ROLE  # noqa: E402  (mesmo papel sem superusuário da regressão)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='edufast-platform:test')
    parser.add_argument('--nome', default=datetime.now().strftime('%Y-%m-%dT%H-%M-%S'))
    parser.add_argument('--amostras', type=int, default=30)
    parser.add_argument('--escala', default='padrao')
    args = parser.parse_args()
    project = 'edufast-desempenho-' + uuid4().hex[:10]
    report = ROOT / '.ci-results' / 'desempenho' / args.nome
    report.mkdir(parents=True, exist_ok=True)
    senha = 'synthetic-perf-only-' + uuid4().hex[:8]
    compose = {'services': {
        'db': {'image': 'postgres:17-alpine', 'cpus': 0.5, 'mem_limit': '512m',
               'environment': {'POSTGRES_DB': 'edufast_desempenho', 'POSTGRES_USER': 'postgres',
                               'POSTGRES_PASSWORD': uuid4().hex, 'APP_DB_USER': 'disposable', 'APP_DB_PASSWORD': senha},
               'configs': [{'source': 'postgres-app-role', 'target': '/docker-entrypoint-initdb.d/10-app-role.sh'}],
               'command': ['postgres', '-c', 'max_connections=30', '-c', 'shared_buffers=128MB'],
               'networks': ['isolated'], 'tmpfs': ['/var/lib/postgresql/data'],
               'healthcheck': {'test': ['CMD-SHELL', 'PGPASSWORD="$$APP_DB_PASSWORD" psql -h 127.0.0.1 -U "$$APP_DB_USER" -d "$$POSTGRES_DB" -tAc "SELECT 1" >/dev/null'],
                               'interval': '2s', 'timeout': '3s', 'retries': 60}},
        'medicao': {'image': args.image, 'cpus': 1.5, 'mem_limit': '1536m', 'working_dir': '/repo', 'networks': ['isolated'],
                    'volumes': [{'type': 'bind', 'source': str(ROOT), 'target': '/repo', 'read_only': True},
                                {'type': 'bind', 'source': str(report), 'target': '/reports'}],
                    'tmpfs': ['/tmp'],
                    'environment': {'DB_URL': f'postgresql+psycopg://disposable:{senha}@db:5432/edufast_desempenho',
                                    'EDUFAST_TEST_DISPOSABLE': '1', 'PYTHON_DOTENV_DISABLED': '1', 'APP_ENV': 'production',
                                    'PYTHONDONTWRITEBYTECODE': '1', 'SECRET_KEY': 'synthetic-performance-only-key-2026-32chars',
                                    'DATA_ENCRYPTION_KEY': base64.urlsafe_b64encode(os.urandom(32)).decode(),
                                    'UPLOAD_FOLDER': '/tmp/uploads', 'TRUSTED_HOSTS': 'localhost', 'PYTHONPATH': '/repo/api:/repo/.github/cicd/desempenho'},
                    'entrypoint': ['python', '/repo/.github/cicd/desempenho/medir.py', '--saida', '/reports',
                                   '--amostras', str(args.amostras), '--escala', args.escala]}},
        'networks': {'isolated': {'internal': True}},
        'configs': {'postgres-app-role': {'content': POSTGRES_APP_ROLE.replace('$', '$$')}}}
    with tempfile.TemporaryDirectory(prefix=project + '-') as temp:
        config = Path(temp) / 'compose.json'
        config.write_text(json.dumps(compose), encoding='utf-8')
        base = ['docker', 'compose', '-p', project, '-f', str(config)]
        try:
            subprocess.run(base + ['up', '-d', '--wait', '--wait-timeout', '180', 'db'], cwd=ROOT, check=True,
                           stdout=subprocess.DEVNULL, timeout=600)
            inicio = time.time()
            with open(report / 'medicao.log', 'wb') as log:
                result = subprocess.run(base + ['run', '--rm', '--no-deps', 'medicao'], cwd=ROOT, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=3600)
            git = lambda *a: subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
            meta = {'commit': git('log', '-1', '--format=%s'), 'arvore_alterada': bool(git('status', '--porcelain', '--', 'api')),
                    'imagem': args.image, 'limites': {'db': '0.5 vCPU / 512 MiB', 'app': '1.5 vCPU / 1536 MiB'},
                    'duracao_s': round(time.time() - inicio), 'sucesso': result.returncode == 0}
            (report / 'execucao.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
            print((report / 'medicao.log').read_text(encoding='utf-8', errors='replace')[-6000:])
            print('Relatório:', report)
            return result.returncode
        finally:
            subprocess.run(base + ['down', '-v', '--remove-orphans'], cwd=ROOT, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=120)


if __name__ == '__main__':
    raise SystemExit(main())
