"""Obtém somente o artefato de uma execução concluída do CI deste repositório."""
import io
import json
import os
import re
import urllib.request
import zipfile


def validate_run(run):
    if (run.get('path') != '.github/workflows/ci.yml' or run.get('status') != 'completed'
        or run.get('conclusion') != 'success' or run.get('head_branch') != 'main'
        or run.get('event') not in ('push', 'workflow_dispatch')
        or not re.fullmatch('[a-f0-9]{40}', run.get('head_sha', ''))):
        raise ValueError('Escolha uma execução bem-sucedida do CI na main.')


def validate_release(release, commit):
    if (release.get('commit') != commit or release.get('image') != 'ghcr.io/samucau1/edufast-2.0'
        or not re.fullmatch(r'sha256:[a-f0-9]{64}', release.get('digest', ''))):
        raise ValueError('Artefato não corresponde à imagem e ao commit validados.')


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    if repo.lower() != 'samucau1/edufast-2.0':
        raise ValueError('Deploy limitado ao repositório EduFast configurado.')
    run_id = os.environ['CI_RUN_ID']
    if not run_id.isdigit():
        raise ValueError('CI_RUN_ID inválido.')
    token = os.environ['GH_TOKEN']

    def api(path):
        request = urllib.request.Request(f'https://api.github.com/repos/{repo}/{path}',
            headers={'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28'})
        # O download redireciona para armazenamento assinado; não encaminhar o token.
        request.add_unredirected_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()

    run = json.loads(api(f'actions/runs/{run_id}'))
    validate_run(run)
    artifacts = json.loads(api(f'actions/runs/{run_id}/artifacts?per_page=100'))['artifacts']
    candidates = [item for item in artifacts if item['name'] == f'release-{run_id}' and not item['expired']]
    if len(candidates) != 1:
        raise ValueError('Artefato de release ausente, expirado ou ambíguo.')
    archive = api(f'actions/artifacts/{candidates[0]["id"]}/zip')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        release = json.loads(zipped.read('release.json'))
    validate_release(release, run['head_sha'])
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'commit={release["commit"]}\ndigest={release["digest"]}\n')
    print('Proveniência da imagem e execução do CI verificadas.')


if __name__ == '__main__':
    main()
