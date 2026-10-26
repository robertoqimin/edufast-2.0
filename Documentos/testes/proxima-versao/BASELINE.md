# Baseline da preparação dos testes — 26/10/2026

[Início da revisão](README.md)

## Infraestrutura

`python .github/cicd/next_stage.py --check`: **5 verificações aprovadas**.

- Catálogo e documentos gerados estão sincronizados.
- Todos os casos previstos são descobertos pelo unittest.
- A rotina destrutiva recusa execução sem a flag de teste.
- A rotina destrutiva recusa banco fora da lista descartável.
- O leitor das asserções JSON funciona com estruturas aninhadas e falha quando o campo não existe.

A imagem de testes foi construída, o Compose exclusivo foi usado, o MySQL ficou saudável e os containers/volumes temporários foram removidos ao final. Isso valida a preparação do ambiente, não as funcionalidades futuras.

## Contratos futuros: RED

Comando executado: `python .github/cicd/next_stage.py --suite all --database both`.

| Suíte | Descobertos | Executados | Resultado observado |
| --- | ---: | ---: | --- |
| Unitários | 47 | 47 | 47 erros pela ausência de `app.services.academic_policy` |
| API em SQLite | 83 | 0 | Preparação bloqueada pelo esquema institucional ausente |
| API em MySQL | 85 | 0 | Preparação bloqueada pelo esquema institucional ausente |
| Integração em SQLite | 10 | 10 | 10 erros pela ausência de `app.migrations` |
| Integração em MySQL | 10 | 10 | 10 erros pela ausência de `app.migrations` |

Os dois casos adicionais do perfil MySQL são os cenários concorrentes API-078/079. Não houve testes ignorados para esconder a falta de implementação. O executor retornou código **1**, indicando que o contrato futuro ainda não foi atendido.

**Nenhum dos 85 cenários de API foi validado funcionalmente nessa rodada.** A falha de preparação impede chegar às requisições; ela é exibida nos relatórios como erro de classe, com zero testes executados. Depois de criar o esquema, os cenários começarão a exercer as rotas e poderão mostrar novas falhas independentes.

As falhas unitárias e de migração também não demonstram correção de regras: os módulos ainda precisam existir. Não foram criados serviços substitutos nem respostas simuladas para produzir testes verdes.

## Desempenho

`python .github/cicd/next_stage.py --suite performance --smoke` também terminou RED, pois a massa de cinco escolas depende do esquema futuro. O relatório permanece com `passed: false` e `qualified: false`.

Não foram obtidos p95, LCP, tempos de interação ou capacidade máxima da próxima versão. Não há afirmação de aprovação de desempenho.

## Regressão atual e próxima fase

O CI da versão existente mantém sua suíte separada. A preparação adiciona somente a verificação de infraestrutura TDD ao CI normal e um workflow manual para os contratos futuros.

As evidências detalhadas locais ficam em `.ci-results/next/`, ignoradas pelo Git, com logs, contagem real, estado da limpeza, commit e hash do catálogo usado em cada execução. Os documentos gerados representam a proposta atual de revisão; alterações de contratos durante a revisão exigem regeneração e nova rodada antes da implementação correspondente.

O próximo passo é o usuário ler e ajustar os contratos. A implementação funcional permanece aguardando essa revisão.
