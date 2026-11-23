"""Executor estrito do TDD futuro; não publica imagem ou implanta software."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE/'next'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Verifica somente infraestrutura e revisão, sem Docker.')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--suite', choices=['unit', 'api', 'integration', 'performance', 'all'], default='all')
    parser.add_argument('--database', choices=['sqlite', 'postgresql', 'both'], default='both')
    parser.add_argument('--smoke', action='store_true', help='Só para performance: não qualifica as metas.')
    parser.add_argument('--duration', type=int, default=600)
    args = parser.parse_args()
    if args.check:
        import unittest
        import check_specs
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(check_specs))
        return 0 if result.wasSuccessful() else 2
    if args.list:
        from catalog import API, UNIT
        for case in API+UNIT:
            print(case['id'], case['title'])
        print(f'{len(API)} API; {len(UNIT)} unitários; 10 integrações em cada banco.')
        return 0
    project = 'edufast-next-'+uuid.uuid4().hex[:10]
    image = project+':tests'
    report = ROOT/'.ci-results'/'next'/project
    report.mkdir(parents=True)
    env = {**os.environ, 'NEXT_TEST_IMAGE': image, 'NEXT_REPORT_DIR': str(report), 'NEXT_BACKEND': 'sqlite', 'NEXT_DB_URL': 'sqlite:///:memory:'}
    base = ['docker', 'compose', '-p', project, '-f', str(PIPELINE/'compose.next.yml')]
    results = []
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    catalog_digest = hashlib.sha256((PIPELINE/'next/catalog.py').read_bytes()).hexdigest()

    def run(command, name, *, required=True):
        print('+', ' '.join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        (report/(name+'.log')).write_bytes(result.stdout+b'\n'+result.stderr)
        print((result.stdout+result.stderr).decode('utf-8', errors='replace'), flush=True)
        if required and result.returncode:
            raise RuntimeError('Falha de ambiente; consulte '+name+'.log')
        return result.returncode

    status = 2
    try:
        run(['docker', 'version'], 'docker')
        run(base+['config', '--quiet'], 'compose')
        run(['docker', 'build', '-f', str(PIPELINE/'Dockerfile'), '-t', image, '.'], 'build')
        suites = ['unit', 'api', 'integration'] if args.suite == 'all' else [args.suite]
        for suite in suites:
            databases = ['sqlite'] if suite == 'unit' else (['postgresql'] if suite == 'performance' else (['sqlite', 'postgresql'] if args.database == 'both' else [args.database]))
            for database in databases:
                directory = report/database/suite
                directory.mkdir(parents=True)
                env.update(NEXT_REPORT_DIR=str(directory), NEXT_BACKEND=database,
                           NEXT_DB_URL='sqlite:///:memory:' if database == 'sqlite' else 'postgresql+psycopg://next_ci:next-fixture-only@db:5432/edufast_next')
                if database == 'postgresql':
                    run(base+['up', '-d', '--wait', '--wait-timeout', '180', 'db'], 'postgresql-start')
                command = base+['run', '--rm', '--no-deps', 'tests', '--suite', suite]
                if suite == 'performance':
                    command = base+['run', '--rm', '--no-deps', '--entrypoint', 'python', 'tests', '/next/benchmark.py', '--report-dir', '/reports', '--duration', str(args.duration)]
                    if args.smoke:
                        command.append('--smoke')
                code = run(command, database+'-'+suite, required=False)
                detail_file = directory/(suite+'.json')
                if not detail_file.exists():
                    raise RuntimeError('Runner não produziu relatório; falha de infraestrutura, não de requisito.')
                detail = json.loads(detail_file.read_text(encoding='utf-8'))
                results.append({'suite': suite, 'database': database, 'exit_code': code, **detail})
        status = 0 if results and all(item['exit_code'] == 0 and item['passed'] for item in results) else 1
    except Exception as error:
        print(str(error), file=sys.stderr)
        results.append({'environment_error': str(error)})
    finally:
        cleaned = run(base+['down', '-v', '--remove-orphans'], 'cleanup', required=False) == 0
        if not cleaned:
            status = 2
        (report/'summary.json').write_text(json.dumps({'status': 'green' if status == 0 else ('red' if status == 1 else 'environment_error'),
                                                     'project': project, 'cleaned': cleaned, 'source_commit': revision,
                                                     'dirty_worktree': dirty, 'catalog_sha256': catalog_digest,
                                                     'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Relatórios:', report)
    return status


if __name__ == '__main__':
    sys.exit(main())
