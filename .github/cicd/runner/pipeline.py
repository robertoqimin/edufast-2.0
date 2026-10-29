def main(ci):
    ci.REPORT.mkdir(exist_ok=True)
    successful = False
    try:
        ci.run(['docker', 'version'])
        ci.compose('config', '--quiet')
        config = ci.json.loads(ci.compose('config', '--format', 'json', capture=True))
        assert not config['services']['app'].get('ports')
        assert not config['services']['db'].get('ports')
        assert config['networks']['backend']['internal'] is True
        revision = ci.os.environ.get('GITHUB_SHA', 'local')
        ci.run(['docker', 'build', '--build-arg', f'VCS_REF={revision}', '-f', str(ci.PIPELINE / 'Dockerfile'), '-t', ci.IMAGE, '.'])
        ci.run(['docker', 'run', '--rm', '-e', 'DOMAIN=school.example.test', '-e', 'ACME_EMAIL=ci@example.test', '--mount', f"type=bind,source={ci.PIPELINE / 'Caddyfile'},target=/etc/caddy/Caddyfile,readonly", 'caddy:2.10.2-alpine', 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile'])
        mount = f'type=bind,source={ci.PIPELINE},target=/pipeline,readonly'
        ci.run(['docker', 'run', '--rm', '--mount', mount, '--entrypoint', 'bash', ci.IMAGE, '-n', '/pipeline/deploy.sh'])
        ci.run(['docker', 'run', '--rm', '--mount', mount, '--entrypoint', 'bash', ci.IMAGE, '-n', '/pipeline/remote.sh'])
        ci.run(['docker', 'run', '--rm', '--mount', mount, '--entrypoint', 'python', ci.IMAGE, '/pipeline/test_deploy.py'])
        ci.compose('run', '--rm', '--no-deps', '-e', 'DB_URL=sqlite:///:memory:', 'tests')
        ci.compose('up', '-d', '--wait', '--wait-timeout', '180', 'db')
        ci.compose('run', '--rm', '--no-deps', 'tests')
        ci.compose('up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'app', 'proxy')
        proxy_config = ci.compose('exec', '-T', 'proxy', 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile', capture=True)
        (ci.REPORT / 'caddy-validation.txt').write_bytes(proxy_config)
        ci.smoke()
        successful = True
        (ci.REPORT / 'image.txt').write_text(ci.IMAGE, encoding='utf-8')
    finally:
        try:
            logs = ci.compose('logs', '--no-color', capture=True)
            (ci.REPORT / 'containers.log').write_bytes(logs)
        finally:
            ci.compose('down', '-v', '--remove-orphans')
        (ci.REPORT / 'summary.json').write_text(ci.json.dumps({'passed': successful, 'project': ci.PROJECT, 'scope': ['SQLite', 'MySQL', 'production image', 'HTTPS', 'backup restore', 'uploads persistence', 'deploy guards']}, indent=2))
    return 0 if successful else 1
