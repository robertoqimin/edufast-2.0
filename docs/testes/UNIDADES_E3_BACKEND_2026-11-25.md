# Unidades — etapa 3: back-end

Data: 25/11/2026. Branch `feature/melhoria-dezembro`. A etapa 3 segue a ficha
[PROPOSTA_010_UNIDADES](../planejamento/PROPOSTA_010_UNIDADES_2026-11-25.md), aprovada pelo
usuário ("ok"): a 010 como está, a Row-Level Security separada na 011, a regra do CPF e a
janela do Supremo.

**Nada foi aplicado em banco real.** A 010 só roda em bancos descartáveis de teste e entra num
banco real pelo `aplicar_migracoes.py`, com backup, junto com este back-end.

## O que foi feito

### 3a — Estrutura

- **Migration 010 versionada:**
  - vai como aprovada para `api/migrations/010_unidades.sql`;
  - o script de desfazer fica em `migrations/desfazer/010_unidades.sql`;
  - o checksum foi registrado no manifesto.
- **Esquema base v10:**
  - gerado dos modelos;
  - a unidade 1, a função e os gatilhos, que não saem dos modelos, ficam marcados na própria
    010 (blocos `-- base:`) e o gerador os copia de lá, numa fonte única;
  - o teste em PostgreSQL confirma que a base v10 é igual ao legado com a 001 a 010 aplicadas
    em sequência.
- **Modelos:**
  - novos: `UnidadeModel`, `UsuarioUnidadeModel` e `TransferenciaUnidadeModel`;
  - `unidade_id` nas 8 tabelas raiz;
  - código da turma e da disciplina, e ano do calendário, únicos por unidade;
  - chaves compostas turma×disciplina e documento×disciplina.
- **Unidade padrão na aplicação:**
  - **Regra:** sem unidade explícita, vale a unidade ativa da requisição; fora de requisição,
    a única unidade da instalação; com várias e nenhuma escolhida, a gravação é recusada (422).
  - **No banco:** continua sem valor padrão, como a 010 aprovada.
  - **Conta nova:** ganha vínculo com a unidade em que foi criada.
  - **Efeito:** com isso, a regressão passou sem mudar os 13 arquivos de teste que criam
    contas e matrículas.
- **SQLite de teste:** gatilhos equivalentes aos do PostgreSQL. A matrícula ou atribuição sem
  vínculo é recusada.
- **Ferramental:**
  - o inventário de migrations passa a reconhecer restrições únicas e chaves estrangeiras pelo
    nome;
  - o esquema legado dos testes cria provisoriamente as tabelas que só nascem em propostas
    posteriores e restaura o "código único" antigo.

### 3b — Unidade ativa

- **Identidade:** a `Identidade` carrega as unidades permitidas e a ativa, conferidas no banco a
  cada requisição (`load_identity`).
  - A sessão só **pede** a unidade.
  - Unidade sem vínculo, vínculo revogado ou "Todas" sem ser super admin respondem 403.
- **Super admin:** vê todas as unidades. Com mais de uma, entra na visão "Todas".
- **Troca de unidade:** `POST /unidade` (CSRF). Com token, o cabeçalho `X-Unidade`.
- **Login:** esquece a unidade da conta anterior no mesmo navegador.

### 3c — Consultas filtradas

- **Como funciona:** um filtro do SQLAlchemy (`do_orm_execute` + `with_loader_criteria`) restringe
  **toda** consulta ORM de uma requisição com unidade ativa. Isso inclui busca por ID,
  carregamento de relações e alterações em lote.
- **Alcance:** cobre as cerca de 165 consultas em 31 arquivos sem editar uma por uma, e as rotas
  futuras já nascem filtradas.

| Tabela | Critério |
| --- | --- |
| Turmas, disciplinas, turma×disciplina, solicitações de alteração, calendários, atestados | `unidade_id` numa unidade visível |
| Alunos e professores | Conta com vínculo ativo ou concluído numa unidade visível |
| Comunicados | Da unidade, ou para todas (`NULL`, do super admin) |
| Documentos e solicitações de documento | Da unidade **ou** de aluno que subiu para ela (regra do usuário) |

- **Fora de outra unidade:** um registro de outra unidade simplesmente não existe para a
  requisição, e as rotas respondem 404, como já faziam para ID inexistente.
- **Exceção do histórico:** o boletim de um aluno que subiu libera as unidades de origem só
  naquela tela e só para leitura (`lendo_historico_de`).
- **Criar na visão "Todas":** pede a unidade (`unidade_para_criar`). Matricular aluno sem vínculo
  com a unidade da turma responde 409 com mensagem, em vez de erro do banco.
- **Aprovações:** a operação do professor é repetida na unidade da solicitação, e o contexto de
  quem aprova é devolvido intacto. Turma ou disciplina pedida pelo professor nasce na unidade da
  solicitação.

### 3d — Regra do CPF (pedido do usuário)

| Cadastro pela secretaria com CPF | Resultado |
| --- | --- |
| Professor que já está na outra unidade | Só ganha o vínculo, com o mesmo login, sem conta nova e sem expor o e-mail |
| Aluno do colégio que **concluiu** | **Sobe para a faculdade**: mesmo cadastro e login, vínculo novo, subida registrada (`cpf_concluinte`), documentos e histórico visíveis à faculdade |
| Aluno que **não concluiu** | 409: "Este CPF pertence a um aluno da instituição que ainda não concluiu o ensino médio. Fale com a secretaria do colégio." Nenhum dado do colégio na resposta |
| Aluno que já subiu | 409: "Este aluno já está na faculdade." |

- **"Concluiu":** `POST /admin/alunos/<id>/concluir`, só a secretaria do colégio. A faculdade
  recebe 404 e o professor, 403.
- **Sem CPF:** `POST /admin/alunos/<id>/levar-para-unidade`, só a unidade de origem, registrado
  como `manual`.
- **Cadastro público:** com várias unidades, o formulário informa a unidade. A conta já nasce
  vinculada a ela e a solicitação vai para a secretaria daquela unidade.

## Testes

| Verificação | Resultado |
| --- | --- |
| Contratos das unidades, SQLite | **14 de 14** (o 10 só roda em PostgreSQL) |
| Contratos das unidades, PostgreSQL | **14 de 15**: o 10 (Row-Level Security) falha como esperado até a 011 |
| Regressão SQLite | **393 OK** (43 pulados, só PostgreSQL) |
| Regressão PostgreSQL 17 descartável | **393 OK** (2 pulados), rodada final em 523 s |
| Migrations em PostgreSQL | Base v10 = legado + 001–010; aplicador sobe legado com dados até a 10, preservando todos os registros |
| Ensaio da 010 e do desfazer (etapa 2) | Dados preservados; recusas esperadas; o desfazer volta ao esquema v9 |

**Contratos acrescentados ou ajustados nesta etapa:**
- **Contrato 15, novo:** a secretaria só vê e decide as solicitações da própria unidade.
- **Correções em contratos meus:**
  - a turma do colégio passou de "1º ano A" para "3º ano B", porque "1º ano A" aparece no texto
    de exemplo do formulário em qualquer unidade;
  - as mensagens de erro passaram a ser lidas do JSON, que escapa os acentos;
  - os vínculos passaram a ser criados antes das matrículas na preparação dos dados.
- **Nenhuma verificação foi relaxada.**

### Desempenho

O filtro entra como subconsulta na mesma consulta e **não aumenta o número de consultas por
página**, que é o orçamento da B3. Tempo no PostgreSQL local, 40 requisições por tela:

| Tela | Sem filtro | Com filtro |
| --- | --- | --- |
| Turmas | 53 ms | 62–64 ms |
| Visão geral | 62 ms | 65–77 ms |
| Diário | 49 ms | 50–61 ms |
| Solicitações | 41 ms | 42–43 ms |

- Os critérios do filtro são montados **uma vez por requisição**.
- Regressão completa em PostgreSQL:
  - **523 s**, contra 498 s antes das unidades (+5%);
  - uma rodada intermediária levou 1.571 s, mas a medição por teste (`--durations`) mostrou que
    foi carga da máquina: os 20 testes mais lentos são os mesmos de antes (aplicador de
    migrations, de 3 a 9 s cada), e nenhum teste de tela aparece entre eles.

## O que falta

| Etapa | Conteúdo |
| --- | --- |
| **4 — Telas** | Seletor de unidade no topo; coluna Unidade e campo de unidade na visão "Todas"; botões "Concluiu o ensino médio" e "Levar para a Faculdade"; unidade no cadastro público; rótulos por unidade (Série/Semestre); checklist "Primeiros passos" por unidade |
| **Supremo** | Janela "Que tipo de instituição é esta?"; migration central 002 (para revisão); criação das unidades na preparação da instalação |
| **011** | Row-Level Security nas tabelas raiz (para revisão), com a exceção do histórico; contrato 10 |
| **Demo** | Colégio Horizonte + Faculdade Horizonte, com verificação no Edge |

## Limitações conhecidas

- O filtro cobre consultas **ORM**. SQL puro (`text(...)`) não é filtrado. Hoje não há nenhuma
  consulta assim nas tabelas raiz, e a 011 (Row-Level Security) cobre esse caso no banco.
- Sem unidade ativa (linha de comando, login, páginas públicas), não há filtro. Comandos de
  administração agem na instalação inteira, como antes.
- Uma conta tem um perfil só (decisão A). Quem é admin no colégio e professor na faculdade usa
  duas contas.
