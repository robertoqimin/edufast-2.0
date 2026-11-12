def database(ci):
    ci.compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -e "CREATE TABLE ci_backup_probe (id INT PRIMARY KEY); INSERT INTO ci_backup_probe VALUES (42);"')
    result = ci.subprocess.run(ci.COMPOSE + ['exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump --single-transaction --no-tablespaces --set-gtid-purged=OFF -u"$MYSQL_USER" "$MYSQL_DATABASE"'], env=ci.ENV, cwd=ci.ROOT, capture_output=True, check=True)
    backup = result.stdout
    assert len(backup) > 100
    ci.compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -e "DROP TABLE ci_backup_probe;"')
    ci.compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"', input=backup)
    restored = ci.compose('exec', '-T', 'db', 'sh', '-c', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -N -u"$MYSQL_USER" "$MYSQL_DATABASE" -e "SELECT id FROM ci_backup_probe"', capture=True)
    assert restored.strip() == b'42'

def uploads(ci, url, context):
    ci.compose('exec', '-T', 'app', 'python', '-c', "from pathlib import Path; Path('/app/uploads/ci.txt').write_text('persisted')")
    uploads = ci.subprocess.run(ci.COMPOSE + ['run', '--rm', '--no-deps', '--entrypoint', 'tar', 'app', '-czf', '-', '-C', '/app', 'uploads'], env=ci.ENV, cwd=ci.ROOT, capture_output=True, check=True).stdout
    ci.compose('exec', '-T', 'app', 'rm', '/app/uploads/ci.txt')
    ci.compose('exec', '-T', 'app', 'tar', '-xzf', '-', '-C', '/app', input=uploads)
    ci.compose('up', '-d', '--no-build', '--force-recreate', '--wait', '--wait-timeout', '180', 'app')
    assert ci.compose('exec', '-T', 'app', 'cat', '/app/uploads/ci.txt', capture=True).strip() == b'persisted'
    assert ci.json.loads(ci.request(url + '/healthz', context)[2])['release'] == ci.IMAGE
