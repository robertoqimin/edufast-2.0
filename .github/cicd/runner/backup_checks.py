PSQL = 'PGPASSWORD="$APP_DB_PASSWORD" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB"'
PG_DUMP = ('PGPASSWORD="$APP_DB_PASSWORD" exec pg_dump -h 127.0.0.1 -U "$APP_DB_USER" -d "$POSTGRES_DB" '
           '--clean --if-exists --no-owner --no-privileges')


def database(ci):
    ci.compose('exec', '-T', 'db', 'sh', '-c', PSQL + ' -c "CREATE TABLE ci_backup_probe (id INT PRIMARY KEY); INSERT INTO ci_backup_probe VALUES (42);"')
    result = ci.subprocess.run(ci.COMPOSE + ['exec', '-T', 'db', 'sh', '-c', PG_DUMP], env=ci.ENV, cwd=ci.ROOT, capture_output=True, check=True)
    backup = result.stdout
    assert len(backup) > 100
    ci.compose('exec', '-T', 'db', 'sh', '-c', PSQL + ' -c "DROP TABLE ci_backup_probe;"')
    ci.compose('exec', '-T', 'db', 'sh', '-c', PSQL + ' --single-transaction -q', input=backup)
    restored = ci.compose('exec', '-T', 'db', 'sh', '-c', PSQL + ' -tAc "SELECT id FROM ci_backup_probe"', capture=True)
    assert restored.strip() == b'42'

def uploads(ci, url, context):
    ci.compose('exec', '-T', 'app', 'python', '-c', "from pathlib import Path; Path('/app/uploads/ci.txt').write_text('persisted')")
    uploads = ci.subprocess.run(ci.COMPOSE + ['run', '--rm', '--no-deps', '--entrypoint', 'tar', 'app', '-czf', '-', '-C', '/app', 'uploads'], env=ci.ENV, cwd=ci.ROOT, capture_output=True, check=True).stdout
    ci.compose('exec', '-T', 'app', 'rm', '/app/uploads/ci.txt')
    ci.compose('exec', '-T', 'app', 'tar', '-xzf', '-', '-C', '/app', input=uploads)
    ci.compose('up', '-d', '--no-build', '--force-recreate', '--wait', '--wait-timeout', '180', 'app')
    assert ci.compose('exec', '-T', 'app', 'cat', '/app/uploads/ci.txt', capture=True).strip() == b'persisted'
    assert ci.json.loads(ci.request(url + '/healthz', context)[2])['release'] == ci.IMAGE
