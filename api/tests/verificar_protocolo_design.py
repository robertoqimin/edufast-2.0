"""Portão estático do protocolo; a inspeção visual continua obrigatória."""
from pathlib import Path
import re
import json
import hashlib


def verificar(root):
    app = root / 'api/app'
    erros = []
    for path in sorted([*(app / 'templates').glob('escola_*.html'), *(app / 'templates').glob('frequencia_*.html'), *(app / 'templates').glob('platform_*.html'), *(app / 'templates').glob('estudo_*.html'), *(app / 'templates').glob('curso_ms04_*.html')]):
        text = path.read_text(encoding='utf-8')
        if "extends 'gestao_base.html'" not in text:
            erros.append(f'{path.name}: não usa o layout compartilhado')
        if re.search(r'<style\b|\sstyle\s*=|\son\w+\s*=|https?://', text, re.I):
            erros.append(f'{path.name}: estilo, evento inline ou recurso externo não permitido')
    css = (app / 'static/css/escola.css').read_text(encoding='utf-8')
    if not all(token in css for token in ('var(--text)', 'var(--surface)', 'var(--accent)', 'var(--school-radius)')):
        erros.append('escola.css: faltam tokens compartilhados')
    if '<style' in (app / 'templates/partials/curso_estilo.html').read_text(encoding='utf-8'):
        erros.append('curso_estilo: estilos precisam estar centralizados')
    for name in ('docs/PROTOCOLO_DESIGN.md', 'AGENTS.md'):
        if not (root / name).is_file():
            erros.append(f'Arquivo obrigatório ausente: {name}')
    reference_root = root / 'docs/design/referencias'
    manifests = sorted(reference_root.glob('*/manifesto.json'))
    if not (reference_root / '2026-10-30-r2/manifesto.json').is_file():
        erros.append('Manifesto da referencia visual ausente')
    for manifest in manifests:
        references = manifest.parent
        try:
            entries = json.loads(manifest.read_text(encoding='utf-8'))['capturas']
            if not entries:
                erros.append('Manifesto visual vazio')
            for entry in entries:
                name = entry['arquivo']
                if Path(name).name != name or not name.endswith('.png'):
                    erros.append('Caminho invalido no manifesto visual')
                    continue
                image = references / name
                if not image.is_file():
                    erros.append(f'Captura ausente: {name}')
                elif hashlib.sha256(image.read_bytes()).hexdigest() != entry['sha256']:
                    erros.append(f'Referencia historica alterada: {name}; registre nova versao sem sobrescrever a anterior')
        except (ValueError, KeyError, TypeError):
            erros.append('Manifesto visual invalido')
    return erros


if __name__ == '__main__':
    erros = verificar(Path(__file__).resolve().parents[2])
    print('\n'.join(erros) if erros else 'Protocolo estático de design aprovado. Inspeção visual exigida separadamente.')
    raise SystemExit(bool(erros))
