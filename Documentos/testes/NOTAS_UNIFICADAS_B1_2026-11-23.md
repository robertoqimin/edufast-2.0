# B1 — Notas unificadas no módulo acadêmico

Data: 23/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«docs: registra revisao das migrations (A5)». Etapa B1 do
[plano de melhoria](../planejamento/PLANO_MELHORIA_2026-11-22.md).

## Objetivo e decisões

O módulo acadêmico (`academico_notas`: período → avaliação → lançamento) passa a ser a
**única fonte de notas** nas telas, como decidido em 22/11.

Em 23/11 ficou decidido também **manter a aprovação por ação**. No diário, cada lançamento,
correção, criação e publicação de avaliação feitos pelo professor continua sendo uma
solicitação que só a secretaria aprova (era o comportamento existente do módulo). Nenhuma
garantia de aprovação foi afrouxada.

## O que mudou

| Área | Antes | Agora |
| --- | --- | --- |
| Painel do professor, aba de notas | Formulário de nota por aluno e disciplina, gravando em `notas` via proposta | Aba "Notas e avaliações": disciplinas atribuídas, avaliações com período, peso, lançadas, pendentes de aprovação e estado, com links para o diário |
| Painel do professor, turmas | Tabela de alunos com formulário de nota | Só nome e matrícula, com aviso de onde lançar |
| Painel do aluno, "Minhas notas" | Lia a tabela `notas` (sem período, sem publicação) | Resumo do boletim **publicado**: disciplina, período, notas publicadas, média e situação. Registros antigos aparecem só como aviso, com link para o boletim |
| `/professor/notas/salvar` | Criava proposta `salvar_nota` | **410**, com o destino `/academico`; não cria proposta |
| Proposta `salvar_nota` pela API | Aceita | **410** |
| Propostas `salvar_nota` antigas pendentes | Aprovar gravava em `notas` | Aprovar → **409**; rejeitar continua funcionando. Título na lista explica: "rejeite e peça o lançamento no diário" |
| Secretaria, detalhe do professor | Últimas notas de `notas` | Últimas notas do diário, com avaliação e período |
| Tabela `notas` | Lida e gravada | **Somente leitura**: preservada, aparece em "Histórico de notas" para reconciliação e no boletim como "registros anteriores"; nunca é apagada |

Arquivos principais: `Codigos/app/services/notas_painel.py` (novo, só leituras),
`aprovacoes_service.py`, `professor_routes.py`, `professor_controller.py`,
`aluno_controller.py`, `pessoas_repository.py`, `admin_presenter.py`,
`aprovacoes_presenter.py`, templates `professor_painel.html`, `aluno_painel.html` e
`partials/workspace_sidebar.html` (rótulo "Notas e avaliações"); `submission.js` perdeu a
sincronização de versão que só servia ao formulário antigo.

Não mudaram: banco, migrations (nenhuma nova), módulo acadêmico, reconciliação de notas
antigas, exportação de privacidade (já trazia o boletim publicado e as notas antigas).

## Testes

**Novos:** `test_notas_unificadas.py`, com 13 casos:
- formulário antigo e API retornam 410 sem efeito;
- proposta antiga pendente só pode ser rejeitada;
- varredura estática garante que nenhum código da aplicação grava, altera ou apaga em `notas`;
- painel do professor leva ao diário, explica quando falta atribuição, mostra pendências e
  respeita atribuição revogada;
- professor lança só com aprovação e versão antiga recebe 409;
- aluno vê só avaliações publicadas, e nota antiga não aparece como nota atual;
- reconciliação de nota antiga preservada;
- detalhe do professor lê o diário.

**Atualizados:**
- `test_approvals_security.py`: o formulário aposentado não tem efeito.
- `test_concurrency.py`:
  - versão e concorrência de notas agora no diário. Duas propostas simultâneas são aceitas,
    e as duas aprovações **simultâneas** deixam só uma valer (200/409);
  - os formulários exigem versão no diário.
- `test_submission.cjs`: caso da sincronização removida.
- Postman: o fluxo de nota passou para o diário (410 no formulário antigo, proposta com token,
  repetição idempotente, versão antiga 409, correção, publicação e boletim do aluno). O
  executor confere 5 propostas aprovadas, **nenhuma linha em `notas`**, nota 9 em
  `academico_notas` e avaliação publicada.

**Fora do escopo:** `.github/cicd/next/catalog.py` (API-051 a 054) descreve a API futura de
várias escolas, com um tipo `salvar_nota` próprio daquela versão; não foi alterado.

### Resultados

Bateria completa em containers sobre o código final, com o fonte conferido como inalterado
durante a regressão. Evidências em `.ci-results/notas-unificadas-b1-2026-11-23/`.

| Etapa | Resultado |
| --- | --- |
| Regressão SQLite | 317 testes aprovados, 43 pulados (os mesmos de antes: concorrência real exige PostgreSQL) |
| Regressão PostgreSQL + concorrência real | 317 aprovados, 2 pulados |
| HTTP real (JWT, multipart, download) | 117 verificações aprovadas |
| `ci.py`: imagem de produção, unitários, regressão, HTTPS, backup/restauração com `pg_dump` e uploads | Aprovado (11 unitários; 317 + 317 testes) |
| Piloto de duas escolas | Aprovado (HTTPS, login, rejeição cruzada, backup, persistência) |
| API de frequência | 117 verificações aprovadas |
| Painel central (Supremo) | 18 testes aprovados |
| Postman SQLite / PostgreSQL | 66 requisições e 76 verificações, 0 falhas em cada; registros e arquivos conferidos |
| Ensaio de atualização legado → v8 | Aprovado na repetição (48 s), ver nota abaixo |

Também passaram localmente: verificador de protocolo de design, `node --test
.github/cicd/test_submission.cjs` (3 testes), `test_ci_characterization.py` (7),
`next_stage.py --check` e `infra/verify.sh` (20 casos), além da suíte completa em SQLite de
arquivo e em memória (317 testes).

**Nota sobre o ensaio:** na bateria, todas as etapas funcionais do ensaio passaram (dados
legados, backup, plano, aplicação, app sobre o banco atualizado, banco recriado e
restaurado). O que travou foi um `docker compose run` que só calcula o `sha256sum` de um
upload restaurado, que estourou o limite de 900 s. Isso é falha do Docker, não da aplicação;
a B1 não altera o ensaio nem a infraestrutura. A etapa foi repetida isoladamente com a mesma
imagem testada e passou inteira em 48 s
(`ensaio-atualizacao-repeticao.log`).

**Execuções descartadas:** duas baterias anteriores foram interrompidas, uma para corrigir
o teste JS e outra para corrigir o defeito 4 abaixo. Interromper a tarefa não encerrou os
processos filhos: duas baterias chegaram a rodar ao mesmo tempo no Docker. Todos os
processos foram encerrados, os projetos de teste descartáveis removidos, e só a execução
única e limpa acima vale como evidência.

### Problemas encontrados e corrigidos durante a etapa

1. **Revisão de código:** a lista "Notas lançadas" do professor mostrava lançamentos de turmas
   cuja atribuição tinha sido revogada (nomes de alunos fora do escopo atual). Passou a filtrar
   pelas atribuições ativas, e um teste foi adicionado.
2. **Teste JS do workflow do GitHub** (`test_submission.cjs`) cobria a função removida e não
   roda na bateria local. Foi achado na revisão, o caso foi removido e a bateria reiniciada.
3. **Bateria em container, 1ª execução:** o painel quebrava com SQLite em memória ("cannot
   start a transaction within a transaction"). A verificação de disponibilidade abria uma
   conexão nova com a sessão já em transação. Passou a inspecionar pela conexão da sessão,
   como o MS04 já fazia. A execução local, em arquivo, não mostrava o defeito; depois da
   correção, a suíte completa passou também em memória.
4. **Bateria em container, 2ª execução:** na imagem de produção (`ci.py`) os testes ficam em
   `/tests` e o código em `/app`, e o teste estático procurava `Codigos/app` por caminho
   relativo. Passou a localizar o pacote pelo import, com checagem de que a varredura não é
   vazia.

## Inspeção visual

Protocolo de design: verificador estático aprovado. Capturas em Edge 1440×1000 e 390×844
(professor, aluno e secretaria), sem rolagem horizontal, registradas em
[referências de 23/11](../design/referencias/2026-11-23-notas-unificadas/COMPARACAO.md) com
manifesto SHA-256. Nenhum CSS novo; nenhuma captura histórica alterada.

**Jornada real no Edge**, numa aba visível, a pedido do usuário. Escola de teste descartável
com 6 alunos, 2 disciplinas e 3 avaliações. Passos:
1. a professora lança 7,50 no diário da Redação e o painel mostra "1 aguardando aprovação";
2. a secretaria aprova;
3. a professora pede publicação;
4. a secretaria aprova;
5. o aluno vê Redação 7,50 e Matemática com média 6,50 ((6,00×2 + 7,50) ÷ 3);
6. o formulário antigo responde 410.

Nenhum erro de JavaScript.

**Limitação já existente, não alterada:** ao trocar de aba nos painéis de professor e aluno,
o primeiro item do menu continua destacado. O script das abas não remove a classe `active`
do template.

## Próxima etapa

B2: aposentar a interface antiga de cursos quando o MS04 está habilitado.
