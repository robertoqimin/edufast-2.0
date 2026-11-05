# Organização dos testes da versão atual

## Mapa das suítes

| Camada/finalidade | Local | Dependências e escopo |
| --- | --- | --- |
| Unitários puros | `unit/test_runtime_config.py` | Apenas Python; limites, padrão e entradas inválidas; não importa Flask nem banco |
| Integração HTTP de limites | `test_runtime_limits.py` | Flask e SQLAlchemy; corpo de requisição e QueuePool SQLite isolado, com recuperação |
| API e persistência | `test_application.py` | Login real, JWT, perfis, cadastros e turmas em banco descartável |
| Contratos administrativos | `test_admin_characterization.py` | Formatos, consultas e validações; combina regras e integração com fixtures |
| Aprovações e permissões | `test_approvals_security.py` | Autorização, propostas, revogação e propriedade de documentos |
| Transações e concorrência | `test_concurrency.py` | Idempotência, rollback, restrições e operações simultâneas; concorrência real exige MySQL |
| Restauração funcional | `test_restauracao.py` | Superperfil, identidade, calendário, regras escolares, privacidade e aprovações |
| Massa de teste manual | `test_manual_fixtures.py` | Repetição, preservação de contas e bloqueio de preparação fora do ambiente autorizado |
| Fluxos HTTP encadeados | `../run_postman.py`, `Documentos/testes/postman/` na raiz | Newman, servidor e SQLite temporários; logins por perfil, propostas/aprovações e efeitos finais |
| JavaScript de submissão | `../test_submission.cjs` | Node; DOM simulado, sem inspeção visual |
| Infraestrutura do CI/deploy | `../test_ci_characterization.py`, `../test_deploy.py` | Contratos do executor e deploy simulado; não são testes do produto |

Os arquivos existentes combinam camadas quando necessário para verificar um comportamento completo. A tabela identifica isso explicitamente. Fixtures compartilhadas permanecem nos caminhos existentes para preservar os imports e os executores de regressão/Postman.

## Comandos

Na raiz, unitários puros em PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'Códigos'
python -m unittest discover -s .github/cicd/tests/unit -v
```

Em Bash: `PYTHONPATH=Códigos python -m unittest discover -s .github/cicd/tests/unit -v`.

Regressão completa isolada em SQLite e MySQL: `python .github/cicd/ci.py`.
Esse executor também valida imagem, HTTPS, restauração e persistência de uploads.
O CI executa os unitários antes da construção e volta a descobri-los na regressão
completa: a repetição é intencional para oferecer feedback rápido e validar o runtime.

Fluxos por perfil: seguir `Documentos/testes/postman/README.md`. Já são obrigatórios
no workflow antes da publicação. Evidências ficam em `.ci-results/`, ignorado pelo Git.

## Descoberta e isolamento

- `unittest discover -s /tests -v` no container percorre a pasta `unit/`, que contém `__init__.py`.
- Mover os três casos de configuração para `unit/` preserva o total de 101 testes da regressão; os dois testes HTTP permanecem em `test_runtime_limits.py`.
- Não executar a descoberta completa diretamente contra a configuração local: várias fixtures apagam e recriam tabelas. Usar exclusivamente o runner descartável.
- Não criar tabelas, rotas ou respostas alternativas para satisfazer testes.
- Contratos futuros ficam em `../next/`, fora da regressão atual; sua consistência é conferida por `next_stage.py --check`, e sua execução funcional usa o workflow TDD separado.
- Os testes não autorizam executar migrations em bancos existentes. Aceitação visual e cobertura das rotas acadêmicas adicionais continuam pendentes no diagnóstico.

Relatórios anteriores registram os caminhos e nomes usados naquela versão. A separação posterior de configuração não altera essas evidências históricas.

## Verificação da reorganização — 05/11/2026

Na base `c12da91`, com esta reorganização local: três unitários aprovados com
`python -S` (sem pacotes externos); descoberta completa em Python 3.12 no container
com SQLite em memória preservou 101 casos, sendo 86 aprovados e 15 exclusivos de
MySQL ignorados; nenhuma falha. Workflow aprovado no actionlint 1.7.7. Log local:
`.ci-results/diagnostico-2026-11-05/organizacao-sqlite.log`.
A rodada MySQL da etapa anterior não foi repetida nesta movimentação dos testes.
