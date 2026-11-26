# Proposta 010 — Unidades: ficha para revisão

Data: 25/11/2026. Situação: **proposta, pendente de aprovação do usuário. Não executada em
nenhum banco real.**

- SQL: [`010_unidades.sql`](../../api/migrations/010_unidades.sql)
- Como desfazer: [`010_unidades_desfazer.sql`](../../api/migrations/desfazer/010_unidades.sql)
- Estudo: [colégio e faculdade na mesma instalação](ESTUDO_UNIDADES_2026-11-25.md)

## Como o sistema vai funcionar

### 1. O Supremo escolhe o tipo de instituição ao cadastrar

No cadastro da escola, o painel Supremo abre a janela **"Que tipo de instituição é esta?"**:

| Opção | O que a instalação recebe |
| --- | --- |
| **Só escola** | Uma unidade de nível básico. Fica igual ao sistema de hoje |
| **Escola com faculdade** | Duas unidades, Colégio (básico) e Faculdade (superior), com secretarias separadas e um super admin que vê as duas |
| **Só faculdade** | Uma unidade de nível superior. É o mesmo sistema da escola, com os nomes da faculdade (Semestre, Curso, Oferta) |

- **Onde a escolha fica:** no cadastro do Supremo (banco central) e na configuração da
  instalação.
- **Como as unidades nascem:** na primeira preparação da instalação, conforme a escolha.
- **Faculdade aberta depois:** se uma escola "só escola" abrir uma faculdade, o Supremo muda
  a opção e a unidade Faculdade é criada sem mexer nos dados do colégio.
- **Banco central:** guardar a escolha exige uma migration pequena no banco central (proposta
  central 002: coluna `modalidade` em `platform_schools`). Ela vem na etapa do Supremo e será
  revisada à parte.

### 2. A regra do aluno que sobe do colégio para a faculdade (pedido do usuário)

**Quando:** a escola tem faculdade, o aluno **concluiu o 3º ano do ensino médio** e a
secretaria da faculdade cadastra um aluno com **o CPF dele**.

**O que o sistema faz:** identifica a pessoa e **sobe o perfil para a faculdade**.
- **Sem conta nova e sem instalação nova:** é o mesmo login e o mesmo cadastro, que ganha o
  vínculo com a faculdade.
- **Histórico e documentos:** o **histórico escolar** e **todos os documentos** do colégio
  passam a aparecer para a secretaria da faculdade, só para leitura. As notas do colégio
  continuam do colégio.
- **Registro:** a subida fica registrada (quem, quando e por quê) e não se repete.
- **Matrícula:** a subida não matricula o aluno em nenhuma turma. A secretaria da faculdade
  matricula como sempre.

**Situações do cadastro na faculdade:**

| CPF informado | Resultado |
| --- | --- |
| Não existe na instituição | Cadastro novo, como hoje |
| Aluno do colégio que **concluiu** o 3º ano | **Sobe automaticamente**, como descrito acima |
| Aluno do colégio que **ainda não concluiu** | Recusado, com a mensagem "Este CPF pertence a um aluno da instituição que ainda não concluiu o ensino médio. Fale com a secretaria do colégio." A faculdade não vê nenhum dado do aluno |
| Aluno que já subiu | Recusado: "Este aluno já está na faculdade" |

**Quem marca "concluiu":**
- até existir a passagem de ano (migration 013), a secretaria do colégio, no detalhe do aluno
  ou para a turma inteira;
- depois, a passagem de ano marca sozinha os alunos aprovados no 3º ano.

**Aluno sem CPF cadastrado:** a secretaria do colégio (ou o super admin) usa **"Levar para a
Faculdade"** no detalhe do aluno. O efeito é o mesmo, e o motivo fica registrado como "manual".

## O que a 010 faz no banco

| # | Mudança | Para quê |
| --- | --- | --- |
| 1 | Tabela `unidades` (nome, nível básico ou superior, estado, rótulos Turma/Série/Período) e a **unidade 1** | A instalação atual vira a unidade 1 |
| 2 | Tabela `usuario_unidades` (conta, unidade, situação `ativo`, `concluido` ou `revogado`) | Quem pode entrar em cada unidade. A situação `concluido` é o que habilita a subida pelo CPF |
| 3 | `unidade_id` em turmas, disciplinas, calendários, comunicados, solicitações de alteração e de documentos, atestados e documentos | Cada secretaria vê só o que é dela |
| 4 | Código da turma e da disciplina, e ano do calendário, únicos **por unidade** | Colégio e faculdade podem usar o mesmo código ("1A") e ter o calendário 2026 cada um |
| 5 | `turmas_disciplinas` com chaves compostas | O banco recusa turma do colégio com disciplina da faculdade |
| 6 | Gatilho em matrículas, professores da turma e atribuições | O banco recusa matricular ou atribuir quem não tem vínculo ativo com a unidade da turma |
| 7 | Tabela `transferencias_unidade` (aluno, origem, destino, autor, motivo `cpf_concluinte` ou `manual`, data), uma por aluno e destino | Registro da subida para a faculdade |

**O que acontece com os dados de hoje:**
- tudo recebe `unidade_id = 1`;
- todas as contas, menos o super admin (que vê todas), ganham vínculo **ativo** com a
  unidade 1;
- comunicados antigos ficam na unidade 1;
- **nenhuma linha é apagada e nenhum valor existente muda.**

**Proteção contra esquecimento:** as colunas novas não têm valor padrão depois da migração.
Se algum código tentar gravar uma turma sem dizer a unidade, o banco recusa, em vez de jogar
a turma no colégio sem ninguém perceber.

## O que a 010 **não** faz

- **Não liga a Row-Level Security.** Ela vira a **proposta 011**, aplicada só depois que o
  back-end informar a unidade em cada transação. Se ligasse junto, a aplicação de hoje
  deixaria de enxergar os dados entre a migration e o código novo.
- **Não muda telas nem regras.** Com uma unidade só, o sistema continua igual. As telas e as
  regras novas vêm nas etapas 3 e 4, com os contratos.
- **Não guarda a escolha do Supremo.** Isso é a proposta central 002, à parte.

## Nova numeração

| Nº | Conteúdo |
| --- | --- |
| **010** | Unidades (esta) |
| 011 | Row-Level Security nas tabelas raiz, com leitura liberada à faculdade do histórico e dos documentos dos alunos que subiram |
| 012 | Ofertas extras do ensino superior (B4, antes 010) |
| 013 | Passagem de ano ou semestre (marca "concluiu" no 3º ano) |
| Central 002 | Tipo de instituição no cadastro do Supremo |

## Ensaio feito (PostgreSQL 17 descartável, 25/11/2026)

O ensaio partiu do esquema atual (v9) com dados de uma escola como as de hoje: admin, aluno,
professor, super admin, turma, disciplina, matrícula, comunicado, calendário, documento e
solicitação. Aplicamos a 010 e conferimos:

| Verificação | Resultado |
| --- | --- |
| Aplicação da 010 | OK, em 0,3 s |
| Dados existentes | Todos na unidade 1; 3 vínculos criados (admin, aluno e professor); super admin sem vínculo; matrícula, documento e comunicado preservados |
| Mesmo código "1A" e mesmo ano 2026 em outra unidade | Aceitos |
| Turma sem unidade | **Recusada** |
| Turma do colégio com disciplina da faculdade (nas duas combinações) | **Recusada** pelas chaves compostas |
| Aluno sem vínculo numa turma da faculdade | **Recusado** pelo gatilho; com o vínculo, aceito |
| Professor com vínculo revogado entrando numa turma | **Recusado** |
| Subida repetida do mesmo aluno | **Recusada** |
| Desfazer com uma faculdade já criada | **Recusado** ("restaure o backup") |
| Desfazer só com a unidade 1 | OK. O esquema voltou **idêntico ao v9** (comparação do `pg_dump`) e os dados ficaram preservados |

## Riscos e como lidar

| Risco | Como fica |
| --- | --- |
| Código antigo grava turma, disciplina ou solicitação sem a unidade | O banco recusa (sem padrão). Por isso a 010 só é aplicada **junto** com o back-end da etapa 3, que sempre informa a unidade, e nunca sozinha sobre o código atual |
| Gatilho deixa a matrícula mais lenta | É uma consulta por chave primária por linha; insignificante no tamanho de uma escola |
| Conta sem vínculo depois da migração | Todas as contas existentes ganham vínculo. Contas novas ganham vínculo no cadastro (etapa 3) |
| CPF ausente ou digitado errado | Sem CPF, não há subida automática; vale o "Levar para a Faculdade" manual. CPF errado cria um cadastro novo, como hoje, sem expor ninguém |
| Voltar atrás | Antes de existir a 2ª unidade, o script de desfazer devolve o esquema v9. Depois, só a restauração do backup feito antes da 010 |

## Para aprovar

1. A 010 como está (estrutura, chaves, gatilho e registro da subida).
2. A divisão: Row-Level Security na 011, depois do back-end.
3. A regra do CPF, com as quatro situações da tabela acima e a opção manual para aluno sem
   CPF.
4. A janela do Supremo com as três opções, e a migration central 002 para guardar a escolha.

Com o seu OK, a implementação começa pela **etapa 3**:
- modelos e serviço de unidades;
- unidade ativa na sessão e guards;
- consultas filtradas;
- a regra do CPF;
- os contratos passando a verde e a regressão de 393 testes preservada.

A cada etapa, eu volto para te consultar.
