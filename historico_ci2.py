from pathlib import Path
import json
import subprocess

p = Path('C:/Users/SGFer/Documents/ProjetoMk1/SamusChat/Educafast')
rows = []
for sha, label in [('f3f147d','Segurança e LGPD'),('e6588d3','Cursos reutilizáveis'),
                   ('31b44b1','Diário por período'),('e6a48b2','Configuração institucional')]:
    values = []
    for name in ('regressao-resumo.json','postman-resumo.json'):
        raw = subprocess.check_output(['git','-c',f'safe.directory={p.as_posix()}','-C',str(p),
            'show',f'{sha}:Documentos/testes/resultados/mysql/{name}'])
        values.append(json.loads(raw))
    rows.append(f'| {label} (`{sha}`) | {values[0]["testes"]} | {values[1]["requisicoes"]} | {values[1]["verificacoes"]} |')
results = p / 'Documentos/testes/resultados/edufast2'
for base in ('sqlite','mysql'):
    data = json.loads((results/base/'comparacao-baseline.json').read_text(encoding='utf-8'))
    assert data['aprovado'] and not data['api_removidos'] and not data['api_falhas']
reg = json.loads((results/'mysql/regressao-resumo.json').read_text(encoding='utf-8'))
api = json.loads((results/'mysql/postman-resumo.json').read_text(encoding='utf-8'))
rows.append(f'| EduFast 2.0 — pasta e CI/CD | {reg["testes"]} | {api["requisicoes"]} | {api["verificacoes"]} |')
report = '''# EduFast 2.0 — comparação dos testes e migração

Data: 24/10/2026. Origem: commit `cb27d3c06c2045dec2cb6b2c84c01188d4b7a55e` do Projeto-Educa-Fast. Dados sintéticos; o ambiente manual do usuário permaneceu separado.

## Comparação histórica

| Entrega | Regressão MySQL | Requisições API | Verificações API |
| --- | ---: | ---: | ---: |
''' + '\n'.join(rows) + '''

As contagens históricas foram extraídas dos JSONs presentes nos commits indicados, não reconstruídas por estimativa. O baseline imediatamente anterior foi copiado para `baselines/pre-2.0/`, incluindo resumos, unittest e JUnit de ambos os bancos.

## Resultado atual

- MySQL 8.4: 84 testes aprovados, sem falhas/erros/ignorados.
- SQLite: 84 cenários, sem falhas/erros, com quatro corridas específicas de MySQL ignoradas explicitamente.
- API em ambos os bancos: 201 requisições e 269 verificações, sem falhas.
- Comparação caso a caso: todas as 269 verificações anteriores mantidas; nenhuma removida ou com falha. Todos os cenários Python anteriores foram mantidos.
- Os três cenários adicionais verificam o portão do CI: cobertura igual aprovada, troca de uma verificação detectada mesmo com totais iguais e falha JUnit não escondida por resumo positivo. Não são três endpoints novos.
- Imagem de produção construída e teste de transporte aprovado: HTTPS com CA confiável, rejeição de CA desconhecida/HTTP simples, HSTS, TLS MySQL, rejeição de conexão sem TLS e de identidade incorreta do banco.
- Inicializador da pasta de trabalho executado após a mudança: ambiente manual pronto na porta 5050, banco existente preservado.
- Scripts Bash passaram na verificação de sintaxe; o script de CD sem configuração foi bloqueado antes de acessar servidor.

Os tempos antigos/novos e suas variações estão nos JSONs de comparação. São execuções locais com carga e ambientes diferentes; não caracterizam benchmark controlado ou SLA.

## Evidências

- [Comparação SQLite](resultados/edufast2/sqlite/comparacao-baseline.json).
- [Comparação MySQL](resultados/edufast2/mysql/comparacao-baseline.json).
- Resumos, logs e JUnit nas mesmas pastas.
- [CI/CD e preparação futura de produção](../operacao/CI_CD.md).
- [Pasta e compatibilidade de caminhos](../operacao/MUDANCA_DE_PASTA.md).

O CI do GitHub repete as verificações em um runner Linux e publica evidências próprias em artefatos. A publicação da imagem só ocorre após o CI e somente na main. O status remoto deve ser conferido na aba Actions; evidências locais não são apresentadas como execução remota.

Não há servidor configurado, domínio de produção ou secrets de implantação. O CD está preparado para o futuro e exige provisionamento, credenciais e plano de backup. Nenhuma produção real foi implantada.
'''
Path('ci2/Documentos/testes/RELATORIO_EDUFAST_2.md').write_text(report,encoding='utf-8')
print('\n'.join(rows))
