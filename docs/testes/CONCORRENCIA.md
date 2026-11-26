# Concorrência, repetição e regressão

Revisão iniciada em 28/10/2026, concluída em 29/10/2026. Base comparada:
`9387748e4cb7c1aee2d156647e4be38a8565a9cb`.

## Correções no código ativo

| Operação | Garantia |
| --- | --- |
| Responder solicitação de documento, aluno ou professor | `UPDATE` condicionado a `status = 'pendente'`, com uma linha afetada; documento, referência e conclusão na mesma transação |
| Criação concorrente da disciplina GERAL | Código único e inserção atômica que reaproveita o registro vencedor |
| Associar professores distintos com disciplina comum | Vínculo docente e disciplinas na mesma transação; inserção atômica do vínculo turma/disciplina já protegido por UNIQUE |
| Editar aluno, professor ou nota | Versão fornecida pelo formulário, conferida no servidor; ORM emite atualização condicionada à versão anterior; concorrente recebe 409 |
| Criar nota ainda inexistente | Versão inicial 0 e UNIQUE aluno/disciplina; apenas uma inserção é confirmada |
| Comunicado, solicitação, atividade e upload avulso | Chave de idempotência única por ator/operação, reservada e concluída na mesma transação da operação |
| Cadastro e vínculos existentes | Constraints únicas preservadas e verificadas por testes concorrentes, incluindo CPF/matrícula disputados por contas distintas |
| Criar administrador | E-mail único; conflito tratado sem substituir contas |
| Inicialização | Sem DDL; produção recusa esquema/constraints incompletos |
| Seed legado | Execução destrutiva desativada; usar create-admin |

Os botões de envio ficam desabilitados durante o processamento, inclusive controles
externos associados ao formulário. Essa camada é apenas UX; todas as garantias acima
ficam no servidor e no banco. A limpeza da foto antiga tolera remoção concorrente.

## Contratos de API

- Edições exigem `versao`. Formulário sem versão: 428; versão antiga: 409.
- Nota nova exige `versao=0`; para editar, usar a versão exibida no formulário.
- Comunicado, solicitação, atividade e upload avulso exigem header `Idempotency-Key`
  ou campo `idempotency_key`, de até 128 caracteres. Ausência: 428.
- Repetir uma chave com o mesmo conteúdo reaproveita o resultado confirmado, sem
  novo registro/arquivo. Conteúdo diferente com a mesma chave: 409.
- Uma nova intenção usa nova chave. Título, nome do arquivo ou conteúdo iguais não
  são considerados duplicidade por si só.
- Responder uma solicitação já concluída retorna 409, inclusive em envio sequencial.
- Rotas web bem-sucedidas continuam usando 302; uploads avulsos JSON continuam 201.
- Integrações antigas que não enviam os novos campos precisam ser atualizadas.

## Comparação e validação

| Verificação | Resultado |
| --- | --- |
| Suíte de API existente no commit base | 18 testes aprovados em SQLite e MySQL |
| Nova suíte de API | 28 testes; 13 exigem MySQL; casos agrupados incluem múltiplas operações |
| Regressão da API existente após a nova suíte | 18 testes aprovados em SQLite e MySQL |
| CI completo Docker | Imagem Linux/Python 3.12, SQLite, MySQL 8.4, testes de deploy, HTTPS/CA/HSTS, cookies, restauração MySQL e uploads aprovados |
| Interface | 3 testes Node: segundo submit, botões associados/recuperação e versão por disciplina |
| Postman/Newman | 32 requisições e 35 assertions aprovadas; quantidade final de registros e arquivos também conferida |

Os testes SQLite pulam explicitamente a concorrência; aprovação de concorrência
vem do MySQL. As edições concorrentes sincronizam as duas leituras de versão antes
da gravação, para não depender apenas da velocidade de duas threads. Cada cliente
usa sua própria sessão HTTP/conexão; o teste administrativo usa processos separados.
As demais disputas usam duas requisições liberadas por barreira e conferência dos
efeitos persistidos. Nenhum resultado comprova isolamento entre escolas, ainda futuro.

Comandos:

```powershell
python .github/cicd/review_mutations.py
# RACE_TEST_DB_URL deve apontar somente para MySQL descartável race_ci_*
python .github/cicd/review_mutations.py --mysql
python .github/cicd/ci.py
node --test .github/cicd/test_submission.cjs
python .github/cicd/run_postman.py --newman CAMINHO/para/newman/bin/newman.js
```

Evidências locais ignoradas pelo Git: `.ci-results/mutations/summary-*.json`, logs
da comparação/regressão, `postman.json` e `.ci-results/summary.json` do CI.
A comparação usa o HEAD do momento; para reproduzir a versão anterior, acrescentar
`--base-ref 9387748e4cb7c1aee2d156647e4be38a8565a9cb`.

## Banco existente e implantação

**Migration preparada para revisão, não executada no banco existente.** Ver
[`api/migrations/README.md`](../../api/migrations/README.md).
Os testes criam esquemas novos e sintéticos, sem executar o arquivo de migration.

Não foi inspecionado banco real nem afirmada ausência de duplicados nele. O preflight
somente leitura informa constraints ausentes e grupos duplicados. Havendo conflito,
preparar remapeamento de referências e arquivamento revisado antes de criar UNIQUE;
não apagar automaticamente. A aplicação deve ser implantada após o esquema aprovado.

Sem Redis, filas, locks de processo ou infraestrutura adicional no produto.
Uma interrupção abrupta do processo pode deixar arquivo físico sem referência;
isso exige reconciliação futura com o banco, não um segundo efeito confirmado na
mesma solicitação. As exceções tratadas nos fluxos têm limpeza e rollback testados.
