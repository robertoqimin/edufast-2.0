"""Mesmo CI em Windows/Linux: Docker Compose >=2.24.4 e Docker ativo."""
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = Path(__file__).resolve().parent
REPORT = ROOT / '.ci-results'
PROJECT = 'edufast-ci-' + uuid.uuid4().hex[:10]
IMAGE = PROJECT + ':tested'
ENV = {**os.environ, 'DOMAIN': 'localhost', 'ACME_EMAIL': 'ci@example.test',
       'SECRET_KEY': 'ci-only-secret-key-with-at-least-32-characters',
       'DB_PASSWORD': 'ci-database-only', 'MYSQL_ROOT_PASSWORD': 'ci-root-only',
       'DB_USER': 'edufast', 'DB_NAME': 'edufast', 'EDUFAST_IMAGE': IMAGE}
COMPOSE = ['docker', 'compose', '-p', PROJECT, '-f', str(PIPELINE/'compose.production.yml'), '-f', str(PIPELINE/'compose.test.yml')]


def run(args, *, capture=False, input=None):
    print('+', ' '.join(map(str, args)), flush=True)
    result = subprocess.run(list(map(str, args)), cwd=ROOT, env=ENV, input=input, stdout=subprocess.PIPE, stderr=subprocess.STDOUT if input is None else subprocess.PIPE)
    if not capture and result.stdout:
        print(result.stdout.decode('utf-8', errors='replace'), flush=True)
    if result.returncode:
        if capture:
            print(result.stdout.decode('utf-8', errors='replace'), flush=True)
        raise RuntimeError(f'Command failed ({result.returncode}): {args[0:3]}')
    return result.stdout


def compose(*args, **kwargs):
    return run(COMPOSE+list(args), **kwargs)


def request(url, context, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, context=context, timeout=15) as response:
        return response.status, dict(response.headers), response.read()


def smoke():
    # Compose de produção real com proxy; somente portas e CA local são substituídas.
    port = compose('port', 'proxy', '443', capture=True).decode().strip().rsplit(':', 1)[1]
    url = f'https://localhost:{port}'
    proxy = compose('ps', '-q', 'proxy', capture=True).decode().strip()
    ca = REPORT/'ci-root.crt'
    run(['docker', 'cp', f'{proxy}:/data/caddy/pki/authorities/local/root.crt', str(ca)])
    context = ssl.create_default_context(cafile=str(ca))
    last_error = None
    for _ in range(30):
        try:
            status, headers, body = request(url+'/healthz', context)
            break
        except (OSError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(1)
    else:
        raise RuntimeError(f'HTTPS not ready: {last_error}')
    assert status == 200 and json.loads(body)['release'] == IMAGE
    assert 'max-age=' in headers['Strict-Transport-Security']
    try:
        request(url+'/healthz', ssl.create_default_context())
    except urllib.error.URLError:
        pass
    else:
        raise AssertionError('Untrusted certificate was accepted')
    assert request(url+'/', context)[0] == 200
    compose('exec', '-T', 'app', 'flask', '--app', 'app:create_app()', 'create-admin', '--email', 'smoke@example.test', '--password', 'ci-smoke-password-123')
    status, headers, _ = request(url+'/login', context, {'email': 'smoke@example.test', 'senha': 'ci-smoke-password-123'})
    assert status == 200 and 'Secure' in headers['Set-Cookie'] and 'HttpOnly' in headers['Set-Cookie']

    # Prova de backup/restauração no banco descartável, sem usar volumes do usuário.
    compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -e "CREATE TABLE ci_backup_probe (id INT PRIMARY KEY); INSERT INTO ci_backup_probe VALUES (42);"')
    # stderr separado para não contaminar o SQL.
    result = subprocess.run(COMPOSE+['exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump --single-transaction --no-tablespaces --set-gtid-purged=OFF -u"$MYSQL_USER" "$MYSQL_DATABASE"'], env=ENV, cwd=ROOT, capture_output=True, check=True)
    backup = result.stdout
    assert len(backup) > 100
    compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -e "DROP TABLE ci_backup_probe;"')
    compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"', input=backup)
    restored = compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -N -u"$MYSQL_USER" "$MYSQL_DATABASE" -e "SELECT id FROM ci_backup_probe"', capture=True)
    assert restored.strip() == b'42'
    compose('exec', '-T', 'app', 'python', '-c', "from pathlib import Path; Path('/app/uploads/ci.txt').write_text('persisted')")
    uploads = subprocess.run(COMPOSE+['run', '--rm', '--no-deps', '--entrypoint', 'tar', 'app', '-czf', '-', '-C', '/app', 'uploads'], env=ENV, cwd=ROOT, capture_output=True, check=True).stdout
    compose('exec', '-T', 'app', 'rm', '/app/uploads/ci.txt')
    compose('exec', '-T', 'app', 'tar', '-xzf', '-', '-C', '/app', input=uploads)
    compose('up', '-d', '--no-build', '--force-recreate', '--wait', '--wait-timeout', '180', 'app')
    assert compose('exec', '-T', 'app', 'cat', '/app/uploads/ci.txt', capture=True).strip() == b'persisted'
    assert json.loads(request(url+'/healthz', context)[2])['release'] == IMAGE
    print('HTTPS, CA, HSTS, login, backup/restauração MySQL e persistência de uploads: OK', flush=True)


def main():
    REPORT.mkdir(exist_ok=True)
    successful = False
    try:
        run(['docker', 'version'])
        compose('config', '--quiet')
        config = json.loads(compose('config', '--format', 'json', capture=True))
        assert not config['services']['app'].get('ports')
        assert not config['services']['db'].get('ports')
        assert config['networks']['backend']['internal'] is True
        revision = os.environ.get('GITHUB_SHA', 'local')
        run(['docker', 'build', '--build-arg', f'VCS_REF={revision}', '-f', str(PIPELINE/'Dockerfile'), '-t', IMAGE, '.'])
        run(['docker', 'run', '--rm', '-e', 'DOMAIN=school.example.test', '-e', 'ACME_EMAIL=ci@example.test',
             '--mount', f'type=bind,source={PIPELINE / "Caddyfile"},target=/etc/caddy/Caddyfile,readonly',
             'caddy:2.10.2-alpine', 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile'])
        mount = f'type=bind,source={PIPELINE},target=/pipeline,readonly'
        run(['docker', 'run', '--rm', '--mount', mount, '--entrypoint', 'bash', IMAGE, '-n', '/pipeline/deploy.sh'])
        run(['docker', 'run', '--rm', '--mount', mount, '--entrypoint', 'bash', IMAGE, '-n', '/pipeline/remote.sh'])
        run(['docker', 'run', '--rm', '--mount', mount, '--entrypoint', 'python', IMAGE, '/pipeline/test_deploy.py'])
        compose('run', '--rm', '--no-deps', '-e', 'DB_URL=sqlite:///:memory:', 'tests')
        compose('up', '-d', '--wait', '--wait-timeout', '180', 'db')
        compose('run', '--rm', '--no-deps', 'tests')
        compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'app', 'proxy')
        proxy_config = compose('exec', '-T', 'proxy', 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile', capture=True)
        (REPORT/'caddy-validation.txt').write_bytes(proxy_config)
        smoke()
        successful = True
        (REPORT/'image.txt').write_text(IMAGE, encoding='utf-8')
    finally:
        try:
            logs = compose('logs', '--no-color', capture=True)
            (REPORT/'containers.log').write_bytes(logs)
        finally:
            # Projeto aleatório exclusivo; nunca executa down no projeto manual ou produção.
            compose('down', '-v', '--remove-orphans')
        (REPORT/'summary.json').write_text(json.dumps({'passed': successful, 'project': PROJECT, 'scope': ['SQLite', 'MySQL', 'production image', 'HTTPS', 'backup restore', 'uploads persistence', 'deploy guards']}, indent=2))
    return 0 if successful else 1


if __name__ == '__main__':
    sys.exit(main())
