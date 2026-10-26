"""Pré-validação sem rede; importada pelos testes e pelo workflow."""
import os
import re
from urllib.parse import urlsplit


def validate(values):
    patterns = {
        'DEPLOY_HOST': r'[a-zA-Z0-9][a-zA-Z0-9.-]*',
        'DEPLOY_USER': r'[a-z_][a-z0-9_-]*',
        'DEPLOY_DIR': r'/[a-zA-Z0-9/_-]+',
        'IMAGE_DIGEST': r'sha256:[a-f0-9]{64}',
        'RELEASE_SHA': r'[a-f0-9]{40}',
    }
    for key, pattern in patterns.items():
        if not re.fullmatch(pattern, values.get(key, '')):
            raise ValueError(f'Configure {key} corretamente.')
    directory = values['DEPLOY_DIR']
    if directory == '/' or '//' in directory or any(part in ('', '.', '..') for part in directory.strip('/').split('/')):
        raise ValueError('DEPLOY_DIR precisa ser um diretório dedicado.')
    port = values.get('DEPLOY_PORT', '22')
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError('DEPLOY_PORT inválida.')
    url = urlsplit(values.get('PUBLIC_URL', ''))
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment:
        raise ValueError('PUBLIC_URL deve ser a origem HTTPS, sem caminho.')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]*', url.hostname):
        raise ValueError('Host público inválido.')
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError('Porta HTTPS inválida.')
    if values.get('BACKUP_CONFIRMED') != 'true':
        raise ValueError('Confirme o provisionamento e o plano de backup/restauração.')
    if not values.get('SSH_KEY', '').strip() or not values.get('KNOWN_HOSTS', '').strip():
        raise ValueError('Configure chave SSH e identidade conhecida do servidor.')


if __name__ == '__main__':
    validate(os.environ)
    print('Configuração de deploy válida; nenhum servidor foi contatado.')
