"""Gera os documentos de revisão a partir dos mesmos casos executados pelos testes."""
import json
from pathlib import Path
from catalog import API, UNIT

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT/'Documentos/testes/proxima-versao'


def generated():
    api = ['# Testes de API — contrato proposto', '',
           'Gerado de `.github/cicd/next/catalog.py`. Revisar antes de implementar. Cada caso começa com a mesma massa fictícia restaurada.', '',
           'Os testes chamam a aplicação real pelo cliente HTTP do Flask e verificam respostas e, quando indicado, o estado do banco. Não são respostas simuladas.', '',
           '| ID | Área | Cenário | Esperado |', '| --- | --- | --- | --- |']
    api += [f'| {c["id"]} | {c["area"]} | {c["title"]} | {c["status"]} |' for c in API]
    for case in API:
        api += ['', f'## {case["id"]} — {case["title"]}', '',
                f'**Perfil:** `{case["actor"] or "não autenticado"}`. **Requisição:** `{case["method"]} {case["path"]}`.', '',
                f'**Resposta esperada:** `{case["status"]}`. **Bancos:** {", ".join(case.get("backends", ["sqlite", "mysql"]))}.', '']
        detail = {k: v for k, v in case.items() if k not in ('id', 'area', 'title', 'actor', 'method', 'path', 'status', 'backends')}
        if detail:
            api += ['```json', json.dumps(detail, ensure_ascii=False, indent=2), '```']
    units = ['# Testes unitários — regras propostas', '',
             'Gerado de `.github/cicd/next/catalog.py`. As funções futuras de `app.services.academic_policy` devem ser puras: sem criar aplicação, abrir banco, enviar email ou acessar rede.', '',
             'Falhas de negócio usam `PolicyError`, com atributos `code` e `status`. Os testes não incluem implementação alternativa dessas regras.', '',
             '| ID | Área | Cenário | Função |', '| --- | --- | --- | --- |']
    units += [f'| {c["id"]} | {c["area"]} | {c["title"]} | `{c["function"]}` |' for c in UNIT]
    for case in UNIT:
        units += ['', f'## {case["id"]} — {case["title"]}', '', f'**Função proposta:** `{case["function"]}`.', '',
                  '```json', json.dumps({k: v for k, v in case.items() if k not in ('id', 'area', 'title', 'function')}, ensure_ascii=False, indent=2), '```']
    return {'API.md': '\n'.join(api)+'\n', 'UNITARIOS.md': '\n'.join(units)+'\n',
            'casos.json': json.dumps({'status': 'proposta_para_revisao', 'api': API, 'unit': UNIT}, ensure_ascii=False, indent=2)+'\n'}


if __name__ == '__main__':
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, content in generated().items():
        (TARGET/name).write_text(content, encoding='utf-8')
    print(f'Revisão gerada: {len(API)} cenários API e {len(UNIT)} regras unitárias.')
