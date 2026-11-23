"""Carga HTTP real em Gunicorn local e PostgreSQL descartável; não simula navegador."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import random
import statistics
import subprocess
import time
import urllib.request
import urllib.error

from fixtures import PASSWORD, assert_disposable, schema, seed


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, max(0, int(len(ordered)*fraction+0.999999)-1))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report-dir', default='/reports')
    parser.add_argument('--duration', type=int, default=600)
    parser.add_argument('--smoke', action='store_true', help='Somente valida o executor; não qualifica desempenho.')
    args = parser.parse_args()
    folder = Path(args.report_dir)
    folder.mkdir(parents=True, exist_ok=True)
    report = {'suite': 'performance', 'passed': False, 'qualified': False, 'phases': []}
    server = None
    stream = None
    try:
        if not args.smoke and args.duration < 600:
            raise ValueError('Ensaio completo exige pelo menos 600 s por patamar; use --smoke para infraestrutura.')
        from app import create_app
        from app.database import engine
        from werkzeug.security import generate_password_hash
        assert_disposable(engine)
        app = create_app()
        if engine.dialect.name != 'postgresql':
            raise ValueError('Benchmark exige PostgreSQL descartável; SQLite não homologa produção.')
        metadata = schema(engine)
        password_hash = generate_password_hash(PASSWORD)
        seed(engine, metadata, app.config['UPLOAD_FOLDER'], password_hash)
        # 5 instituições / 1.000 alunos por escola, sem documentos reais.
        with engine.begin() as db:
            for school in (3, 4, 5):
                db.execute(metadata.tables['escolas'].insert().values(id=school, nome=f'Escola Carga {school}', codigo=f'CARGA{school}', status='ativa'))
                identity = 20000+school
                db.execute(metadata.tables['usuarios'].insert().values(id=identity, email=f'carga{school}@example.test', senha=password_hash, tipo='usuario'))
                db.execute(metadata.tables['participacoes_escolas'].insert().values(id=identity, escola_id=school, usuario_id=identity, papel='gestor', status='ativa'))
            identity = 1000
            for school in range(1, 6):
                for index in range(998 if school in (1, 2) else 1000):
                    identity += 1
                    db.execute(metadata.tables['usuarios'].insert().values(id=identity, email=f'aluno{identity}@example.test', senha=password_hash, tipo='usuario'))
                    db.execute(metadata.tables['alunos'].insert().values(id=identity, escola_id=school, usuario_id=identity, nome=f'Aluno Carga {identity}', matricula=f'CARGA{index}'))
        stream = (folder/'gunicorn.log').open('wb')
        server = subprocess.Popen(['gunicorn', '--bind=127.0.0.1:8088', '--workers=1', '--threads=4', 'app:create_app()'], cwd='/app', stdout=stream, stderr=subprocess.STDOUT)

        def request(path, data=None, token=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer '+token
            req = urllib.request.Request('http://127.0.0.1:8088'+path, headers=headers, data=json.dumps(data).encode() if data is not None else None)
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status, response.read()

        for _ in range(60):
            try:
                request('/healthz')
                break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError('Gunicorn encerrou antes de ficar pronto.')
                time.sleep(0.5)
        else:
            raise RuntimeError('Gunicorn não ficou pronto.')
        actors = ['secretaria_a', 'gestor_b', 'carga3', 'carga4', 'carga5']
        tokens = []
        for school, actor in enumerate(actors, 1):
            _, raw = request('/api/v1/auth/login', {'email': actor+'@example.test', 'senha': PASSWORD})
            token = json.loads(raw)['data']['access_token']
            request('/api/v1/contexto', {'escola_id': school}, token)
            tokens.append(token)
        if not args.smoke:
            warm_until = time.monotonic()+30
            while time.monotonic() < warm_until:
                request('/api/v1/escolas/1/alunos?per_page=25', token=tokens[0])
                time.sleep(0.2)
        duration = 5 if args.smoke else args.duration
        for sessions in (1, 10, 25):
            deadline = time.monotonic()+duration

            def worker(identity):
                rng = random.Random(identity)
                samples = []
                school = identity % 5 + 1
                token = tokens[school-1]
                sequence = 0
                while time.monotonic() < deadline:
                    sequence += 1
                    choice = rng.random()
                    payload = None
                    if choice < 0.7:
                        kind, path = 'read', f'/api/v1/escolas/{school}/alunos?per_page=25'
                    elif choice < 0.9:
                        kind, path = 'search', f'/api/v1/escolas/{school}/alunos?q=Carga&page=1&per_page=25'
                    else:
                        kind, path = 'write', f'/api/v1/escolas/{school}/alunos'
                        code = f'LOAD-{sessions}-{identity}-{sequence}'
                        payload = {'nome': 'Aluno Medição', 'email': code.lower()+'@example.test', 'matricula': code}
                    start = time.perf_counter()
                    error = None
                    try:
                        status, body = request(path, payload, token)
                        parsed = json.loads(body)
                        if status not in (200, 201) or 'data' not in parsed:
                            raise AssertionError('Resposta inválida.')
                        records = parsed['data'] if isinstance(parsed['data'], list) else [parsed['data']]
                        if any(row.get('escola_id') != school for row in records):
                            raise AssertionError('Resposta sem escopo institucional correto.')
                    except Exception as caught:
                        error = str(caught)
                    samples.append((kind, time.perf_counter()-start, error))
                    time.sleep(rng.uniform(0.2, 1))
                return samples

            started = time.monotonic()
            with ThreadPoolExecutor(max_workers=sessions) as pool:
                samples = [sample for batch in pool.map(worker, range(sessions)) for sample in batch]
            elapsed = time.monotonic()-started
            phase = {'sessions': sessions, 'seconds': elapsed, 'requests': len(samples), 'requests_per_second': len(samples)/elapsed,
                     'errors': [error for _, _, error in samples if error], 'latency_ms': {}}
            for kind in ('read', 'search', 'write'):
                values = [seconds*1000 for key, seconds, error in samples if key == kind and not error]
                phase['latency_ms'][kind] = {'samples': len(values), 'p95': percentile(values, 0.95) if values else None,
                                           'median': statistics.median(values) if values else None}
            report['phases'].append(phase)
        passed = all(not phase['errors'] for phase in report['phases'])
        if not args.smoke:
            for phase in report['phases']:
                for kind, limit in [('read', 500), ('search', 500), ('write', 1000)]:
                    group = phase['latency_ms'][kind]
                    passed = passed and group['samples'] >= 100 and group['p95'] <= limit
        report.update(passed=passed, qualified=passed and not args.smoke, initial_students=5000,
                      limits={'tests_cpu': 1, 'tests_memory_mib': 768, 'database_cpu': 1, 'database_memory_mib': 1024},
                      scope='HTTP local Gunicorn + PostgreSQL; gerador e servidor compartilham CPU; sem navegador, proxy, rede limitada ou homologação do host físico')
        peak = Path('/sys/fs/cgroup/memory.peak')
        report['generator_and_app_peak_memory_bytes'] = int(peak.read_text().strip()) if peak.exists() else None
    except Exception as error:
        report['error'] = str(error)
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if stream is not None:
            stream.close()
        (folder/'performance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
