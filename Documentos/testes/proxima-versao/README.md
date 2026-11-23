# Revisão dos testes antes da implementação

**Situação: contratos propostos para sua leitura. Nenhuma funcionalidade nova foi implementada.**

[Revisão técnica da etapa 2 — 05/11/2026](REVISAO_2026-11-05.md): rastreabilidade, conflitos com a versão atual, recomendações e critérios para iniciar a implementação.

[Matriz de permissões e transições](PERMISSOES_E_TRANSICOES.md): detalhamento do incremento 2.1 e conciliação inicial dos contratos docentes no incremento 2.2.

Esta etapa segue o ciclo TDD: definir resultado esperado → observar o teste falhar pelo recurso ausente → implementar → obter aprovação dos testes → refatorar preservando os resultados. A implementação funcional só começa depois da revisão solicitada pelo usuário.

## Ordem sugerida de leitura

1. [Contrato e decisões propostas](CONTRATO.md): comportamento, perfis, respostas e preparação dos dados.
2. [90 cenários de API](API.md): requisições, perfis, resultados e verificações do banco.
3. [47 regras unitárias](UNITARIOS.md): entradas e saídas das regras isoladas.
4. [Integração e migrações](INTEGRACAO.md): 10 cenários em cada banco, concorrência e preservação de dados.
5. [Desempenho e interface](DESEMPENHO_E_INTERFACE.md): limites, executor HTTP e roteiro de aceitação visual.
6. [Validação da infraestrutura e baseline RED](BASELINE.md).

Os documentos API/UNITARIOS e [casos.json](casos.json) são gerados do mesmo catálogo usado pelos testes. Alterações de regra devem aparecer primeiro nesse contrato, sem enfraquecer testes apenas para acomodar a implementação.

## O que será coberto

| Entrega | Evidências propostas |
| --- | --- |
| Autenticação | API-001, 086 a 090; credenciais erradas, login incompleto e tokens adulterados/expirados |
| Várias escolas | API-001 a 012, 085; UNIT-001 a 006; INT-006 e 008 |
| Participações e convites | API-010, 013 a 018, 079; UNIT-029 a 032 |
| Períodos letivos | API-019 a 022, 045; UNIT-007 a 010, 015 |
| Pessoas | API-023 a 032, 083; INT-008 |
| Turmas e disciplinas | API-033 a 040; UNIT-016 e 017 |
| Matrículas e transferências | API-041 a 047, 078; UNIT-011 a 017; INT-006 e 007 |
| Docência, notas e atividades | API-048 a 056; UNIT-018 a 028; INT-009 e 010 |
| Documentos e fotos | API-057 a 064, 075, 080 a 082; UNIT-037 a 040 |
| Comunicados | API-065 a 067; UNIT-045 a 047 |
| Painel, buscas e exportação | API-068 a 071; UNIT-033 a 036 |
| Auditoria | API-072, junto da verificação de gravação no banco |
| Compatibilidade e cache | API-073 a 077, 080 a 082, 084; UNIT-041 a 044 |
| Migração de instalação existente | INT-001 a 005; esquema legado congelado em SQLite/MySQL (snapshot histórico) |
| Desempenho em hardware modesto | Executor HTTP com limites; roteiro de navegador/equipamento real |

São cenários iniciais de aceite, não garantia de cobertura exaustiva. Novas regras descobertas na revisão devem receber testes antes de serem implementadas.

## Executar localmente

Requisitos do executor: Python 3.10+, Docker ativo e Compose 2.24.4+. Os testes da aplicação rodam em Python 3.12 no container. Na raiz do repositório:

```bash
# Só infraestrutura, descoberta dos testes e sincronização dos documentos:
python .github/cicd/next_stage.py --check

# Listar contratos sem acessar banco:
python .github/cicd/next_stage.py --list

# Regras unitárias, sem banco externo:
python .github/cicd/next_stage.py --suite unit

# Contratos de API nos dois bancos:
python .github/cicd/next_stage.py --suite api --database both

# Migrações e integridade:
python .github/cicd/next_stage.py --suite integration --database both

# Rodada funcional completa; não inclui carga longa:
python .github/cicd/next_stage.py --suite all --database both

# Apenas preparar/validar o executor de carga (não homologa metas):
python .github/cicd/next_stage.py --suite performance --smoke
```

Saídas: `0` = suíte solicitada passou integralmente; `1` = contratos ainda falham; `2` = problema de ambiente/infraestrutura. O comando `--check` passar significa somente que a infraestrutura está consistente.

Os resultados são salvos em `.ci-results/next/edufast-next-<id>/`: logs, JSON por suíte e resumo com commit, indicação de alterações locais e hash do catálogo. `discovered` informa testes descobertos; `executed` informa quantos executaram. Falha na preparação da classe pode impedir todos os cenários de API de começar, e isso nunca é contado como aprovação.

## Isolamento do ambiente

- Compose exclusivo: [compose.next.yml](../../../.github/cicd/compose.next.yml).
- Projeto aleatório `edufast-next-*`, rede interna sem portas publicadas e volume PostgreSQL próprio.
- Dados totalmente fictícios; nenhum email é enviado a serviços externos.
- A rotina destrutiva exige flag de teste e aceita somente SQLite em memória ou o PostgreSQL `edufast_next`, usuário `next_ci`, host interno `db`.
- Não usa `.env`, uploads, bancos ou volumes do ambiente manual/produção.
- Ao terminar, remove somente os containers e volumes do projeto criado pelo executor. Relatórios permanecem para leitura.
- O container de testes usa root apenas para gravar relatórios do runner; não monta o socket Docker nem diretórios pessoais. A imagem de produção continua com seu usuário sem root.

## Relação com CI/CD

O CI normal continua executando a regressão existente e verifica somente a integridade do catálogo TDD. Os contratos futuros têm workflow manual separado: **TDD - Próxima versão (contratos em revisão)**.

Esse workflow falha de verdade enquanto faltarem os recursos. Não usa `skip`, `expectedFailure`, `xfail` ou `continue-on-error` para transformar falta de implementação em aprovação. Não publica imagem nem aciona deploy.

Após implementar e aprovar cada grupo, sua execução deve virar requisito do CI normal antes de liberar a funcionalidade correspondente. Até lá, os contratos futuros não comprovam a prontidão da versão publicada.

## Depois da sua leitura

Revisar os códigos de resposta, os papéis, as transições e as decisões destacadas em [CONTRATO.md](CONTRATO.md). Em seguida, implementar primeiro migrações e isolamento institucional, depois os fluxos acadêmicos. Cada mudança deve demonstrar quais casos passaram de RED para GREEN e quais continuam pendentes.
