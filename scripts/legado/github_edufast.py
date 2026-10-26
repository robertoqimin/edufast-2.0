"""Operações GitHub autorizadas; credencial fica apenas em memória."""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error


def autenticar():
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'}
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                            capture_output=True, text=True, env=env)
    if result.returncode:
        raise RuntimeError('A autenticação local do GitHub não está disponível em modo não interativo.')
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    token = fields.get('password')
    if not token:
        raise RuntimeError('Nenhuma credencial GitHub disponível.')
    return token


class Github:
    def __init__(self):
        self.token = autenticar()

    def request(self, path, method='GET', data=None):
        req = urllib.request.Request('https://api.github.com' + path,
            data=json.dumps(data).encode() if data is not None else None, method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'EduFast-migration', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else None
        except urllib.error.HTTPError as exc:
            body = json.loads(exc.read() or b'{}')
            raise RuntimeError(f'GitHub HTTP {exc.code}: {body.get("message", "Falha na API")}') from None


if __name__ == '__main__':
    api = Github()
    user = api.request('/user')
    if user['login'].lower() != 'samucau1':
        raise RuntimeError('A conta autenticada não é Samucau1. Nenhuma alteração executada.')
    print('Conta autenticada:', user['login'])
    if sys.argv[1:] == ['criar']:
        try:
            repo = api.request('/repos/Samucau1/edufast-2.0')
            raise RuntimeError('O repositório já existe; não será sobrescrito.')
        except RuntimeError as exc:
            if 'HTTP 404:' not in str(exc):
                raise
        repo = api.request('/user/repos', 'POST', {'name': 'edufast-2.0', 'private': True,
            'description': 'EduFast 2.0 — gestão escolar configurável, cursos e boletim.', 'auto_init': False})
        print(json.dumps({'url': repo['html_url'], 'privado': repo['private']}, ensure_ascii=False))
