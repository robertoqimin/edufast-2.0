def https_login(ci):
    port = ci.compose('port', 'proxy', '443', capture=True).decode().strip().rsplit(':', 1)[1]
    url = f'https://localhost:{port}'
    proxy = ci.compose('ps', '-q', 'proxy', capture=True).decode().strip()
    ca = ci.REPORT / 'ci-root.crt'
    ci.run(['docker', 'cp', f'{proxy}:/data/caddy/pki/authorities/local/root.crt', str(ca)])
    context = ci.ssl.create_default_context(cafile=str(ca))
    last_error = None
    for _ in range(30):
        try:
            status, headers, body = ci.request(url + '/healthz', context)
            break
        except (OSError, ci.urllib.error.URLError) as error:
            last_error = error
            ci.time.sleep(1)
    else:
        raise RuntimeError(f'HTTPS not ready: {last_error}')
    assert status == 200 and ci.json.loads(body)['release'] == ci.IMAGE
    assert 'max-age=' in headers['Strict-Transport-Security']
    try:
        ci.request(url + '/healthz', ci.ssl.create_default_context())
    except ci.urllib.error.URLError:
        pass
    else:
        raise AssertionError('Untrusted certificate was accepted')
    assert ci.request(url + '/', context)[0] == 200
    ci.compose('exec', '-T', 'app', 'flask', '--app', 'app:create_app()', 'create-admin', '--email', 'smoke@example.test', '--password', 'ci-smoke-password-123')
    status, headers, _ = ci.request(url + '/login', context, {'email': 'smoke@example.test', 'senha': 'ci-smoke-password-123'})
    assert status == 200 and 'Secure' in headers['Set-Cookie'] and ('HttpOnly' in headers['Set-Cookie'])
    return (url, context)
