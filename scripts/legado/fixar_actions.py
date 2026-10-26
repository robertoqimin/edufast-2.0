from pathlib import Path
import json
from github_edufast import Github
api = Github()
pins = {}
for repository in ('checkout', 'setup-python', 'upload-artifact'):
    obj = api.request(f'/repos/actions/{repository}/git/ref/tags/v7')['object']
    while obj['type'] == 'tag':
        obj = api.request(f'/repos/actions/{repository}/git/tags/{obj["sha"]}')['object']
    if obj['type'] != 'commit':
        raise RuntimeError('A referência da action não aponta para commit.')
    pins[f'actions/{repository}'] = obj['sha']
for path in Path(__file__).resolve().parents[2].joinpath('Documentos/arquivo/ci2/.github/workflows').glob('*.yml'):
    content = path.read_text(encoding='utf-8')
    for name, sha in pins.items():
        content = content.replace(f'uses: {name}@v7', f'uses: {name}@{sha} # v7')
    path.write_text(content, encoding='utf-8')
print(json.dumps(pins))
