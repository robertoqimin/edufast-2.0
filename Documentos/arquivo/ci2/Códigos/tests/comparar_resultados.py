"""Compara evidências reais com baseline; falha se perder cobertura ou houver regressão."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def casos_api(path):
    root = ET.parse(path).getroot()
    casos, falhas = Counter(), []
    for suite in root.findall('testsuite'):
        for case in suite.findall('testcase'):
            key = suite.attrib['name'] + ' / ' + case.attrib['name']
            casos[key] += 1
            if case.find('failure') is not None or case.find('error') is not None:
                falhas.append(key)
    return casos, falhas


def casos_python(path):
    return set(re.findall(r'^\w+ \(([^)]+)\) \.\.\. ', path.read_text(encoding='utf-8'), re.M))


def comparar(baseline, resultados):
    problemas, suites = [], {}
    for nome in ('regressao', 'postman'):
        anterior = json.loads((baseline / f'{nome}-resumo.json').read_text(encoding='utf-8'))
        atual = json.loads((resultados / f'{nome}-resumo.json').read_text(encoding='utf-8'))
        if not atual.get('aprovado') or atual.get('falhas', 0) or atual.get('erros', 0):
            problemas.append(f'{nome}: execução atual não aprovada')
        contagens = ('testes',) if nome == 'regressao' else ('requisicoes', 'verificacoes')
        for campo in contagens:
            if atual[campo] < anterior[campo]:
                problemas.append(f'{nome}: redução de {campo} de {anterior[campo]} para {atual[campo]}')
        if atual.get('ignorados', 0) > anterior.get('ignorados', 0):
            problemas.append(f'{nome}: mais cenários ignorados que no baseline')
        suites[nome] = {'anterior': anterior, 'atual': atual,
            'variacao_duracao_percentual': round((atual['duracao_segundos'] / anterior['duracao_segundos'] - 1) * 100, 2)
            if anterior.get('duracao_segundos') else None}
    old, _ = casos_api(baseline / 'postman-junit.xml')
    new, falhas = casos_api(resultados / 'postman-junit.xml')
    removidos, adicionados = old - new, new - old
    if removidos:
        problemas.append(f'API: {sum(removidos.values())} verificações do baseline ausentes')
    if falhas:
        problemas.append(f'API: {len(falhas)} verificações falharam')
    old_py = casos_python(baseline / 'regressao-unittest.txt')
    new_py = casos_python(resultados / 'regressao-unittest.txt')
    if old_py - new_py:
        problemas.append(f'Python: {len(old_py - new_py)} cenários anteriores ausentes')
    return {'aprovado': not problemas, 'problemas': problemas, 'suites': suites,
        'api_removidos': dict(removidos), 'api_adicionados': dict(adicionados), 'api_falhas': falhas,
        'python_removidos': sorted(old_py - new_py), 'python_adicionados': sorted(new_py - old_py),
        'limite': 'Tempos são informativos; não são um teste de desempenho controlado nem um SLA.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--resultados', type=Path, required=True)
    args = parser.parse_args()
    report = comparar(args.baseline, args.resultados)
    args.resultados.mkdir(parents=True, exist_ok=True)
    (args.resultados / 'comparacao-baseline.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['aprovado'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
