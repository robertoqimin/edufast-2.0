# Unidades: colégio e faculdade na mesma instalação

Data: 25/11/2026. Branch `feature/melhoria-dezembro`. Este documento é um estudo e não
executa nada em banco. Ele vem antes da B4 (ofertas do ensino superior) e da passagem de ano,
porque as duas passam a funcionar **dentro de uma unidade**.

## O que o usuário pediu

> Se a escola for ligada a uma faculdade, o super admin vê todo mundo. Os administradores se
> dividem: um administrador da escola e um da universidade, que administra os alunos e os
> professores da universidade. As secretarias não podem se misturar. Vai precisar de logins
> e caminhos diferentes e de mudanças no back-end e no banco.

## Decisões registradas (25/11/2026)

| # | Pergunta | Decisão do usuário |
| --- | --- | --- |
| 1 | Estrutura | **Uma instalação com unidades** (Colégio e Faculdade), e não duas instalações separadas |
| 2 | Pessoa com vínculo nas duas unidades (professor dos dois, ex-aluno do colégio na faculdade) | **Um login**, com troca de unidade |
| 3 | Entrada | **Mesmo endereço**: uma tela de login só, que leva cada pessoa à unidade do seu vínculo |

## Como funciona hoje

- Cada instalação é uma escola só. Os perfis ficam em `usuarios.tipo`, com quatro valores:
  `super_admin`, `admin`, `professor` e `aluno`. Eles valem para a instalação inteira, e o
  `admin` enxerga todos os alunos, turmas e professores.
- **Ponto forte:** a identidade é recarregada do banco a cada requisição (`load_identity` em
  `identidade_service.py`), e acesso revogado cai na hora. A unidade ativa entra nesse mesmo
  ponto.
- **Tamanho da mudança:** 160 rotas, 55 tabelas e 49 consultas diretas a alunos, turmas e
  professores sem nenhum filtro de "parte da escola".
- **O que já ajuda:** quase tudo o que é acadêmico depende de **turma** ou de **disciplina**:
  - notas e avaliações, chamada, materiais e abas, cursos ofertados e atribuições;
  - por isso, ao dar unidade à turma e à disciplina, a maior parte das tabelas herda a
    unidade sem coluna nova.

## O modelo

### Unidade

Tabela nova `unidades`:

| Coluna | Exemplo |
| --- | --- |
| `nome` | Colégio Horizonte / Faculdade Horizonte |
| `nivel` | `basico` / `superior` |
| Rótulos | Série ou Semestre; Turma, Oferta ou Eletiva; Ano letivo ou Período. Substitui a `escola_termos` da proposta B4 |
| `estado` | `ativa` / `arquivada` |

Na migração, a instalação existente vira **uma unidade** (o Colégio), e todos os dados atuais
vão para ela, sem perda e sem mudar o comportamento de quem tem uma unidade só.

### Vínculo da pessoa com a unidade

Tabela nova `usuario_unidades`, com usuário, unidade e estado.

| Perfil (`usuarios.tipo`) | Vê |
| --- | --- |
| `super_admin` | **Todas** as unidades, sem precisar de vínculo. Tem o seletor "Colégio / Faculdade / Todas" |
| `admin` | Só as unidades do seu vínculo. O admin do colégio não vê a faculdade, e o contrário também vale |
| `professor` | Só as unidades do vínculo e, dentro delas, só as turmas atribuídas (como hoje) |
| `aluno` | Só as unidades do vínculo e, dentro delas, só as turmas em que está matriculado (como hoje) |

- **Perfil único por conta:** o perfil continua em `usuarios.tipo`, um por conta. Quem tem
  vínculo nas duas unidades tem **o mesmo perfil nas duas**.
- **Perfis diferentes:** quem for admin no colégio e professor na faculdade precisa de duas
  contas. Ver a decisão A.

### O que recebe a coluna `unidade_id`

**Tabelas raiz** (8), que não dependem de turma nem de disciplina:

| Tabela | Por quê |
| --- | --- |
| `turmas` | Toda a vida acadêmica sai daqui |
| `disciplinas` | Matemática do colégio ≠ Cálculo da faculdade |
| `escola_calendarios` (eventos e políticas herdam) | O colégio tem ano letivo e bimestres; a faculdade, semestres |
| `comunicados` | Comunicado da unidade ou, se enviado pelo super admin, para todas |
| `solicitacoes_alteracoes` | Cada secretaria vê e aprova só as solicitações da sua unidade |
| `solicitacoes_documentos`, `documentos` | Documento pedido ao colégio não aparece para a faculdade |
| `frequencia_atestados` | O atestado é analisado pela secretaria da unidade |

**Herdam a unidade** pela turma ou pela disciplina, sem coluna nova:
- turmas × disciplinas, matrículas e atribuições;
- notas e avaliações, períodos acadêmicos e chamadas;
- materiais e abas, cursos (pela disciplina) e progresso.

**Continuam da instituição:**
- `escola_identidade`: um endereço só, com nome e cores da instituição; o nome da unidade
  aparece no topo;
- privacidade (LGPD: um controlador só);
- limites de login, idempotência e o registro de migrations.

### Garantias no banco

1. **Mesma unidade nas ligações:** turma e disciplina ligadas (`turmas_disciplinas`) precisam
   ser da mesma unidade, e a matrícula também.
   - Isso fica garantido por chave estrangeira composta (`id, unidade_id`), e não só pelo
     código. Assim, uma turma do colégio não recebe Cálculo da faculdade nem por erro.
2. **Unidade conferida a cada requisição:**
   - a unidade ativa fica na sessão, mas é **conferida no banco** a cada requisição, junto
     com a identidade;
   - trocar de unidade não carrega papéis nem dados de uma unidade para a outra;
   - o ID enviado pelo navegador nunca é aceito sem essa conferência.
3. **Row-Level Security** (PostgreSQL) nas tabelas raiz, como segunda barreira:
   - mesmo que uma consulta esqueça o filtro, o banco não devolve linhas de outra unidade;
   - a aplicação informa ao banco as unidades permitidas no início de cada transação;
   - o SQLite dos testes rápidos não tem esse recurso, então a barreira é testada na
     regressão em PostgreSQL.
4. **Resposta para recurso de outra unidade:** o servidor responde **404**, e não 403, para
   não confirmar que o recurso existe.

### Login e caminhos (mesmo endereço)

- **Com uma unidade só:** a pessoa entra direto nela, como hoje.
- **Com duas:** vai para a última unidade usada e troca pelo seletor no topo.
- **Super admin:** entra na visão "Todas":
  - as listas mostram a coluna Unidade;
  - para criar turma, disciplina ou aluno, ele escolhe a unidade antes.
- **Caminhos:** as telas continuam as mesmas (`/admin/...`, `/academico`, `/estudos`...) e
  mostram só a unidade ativa. Isso mantém "uma tela por tarefa" (U5) e evita manter duas
  cópias de cada tela.
- **Menu e textos** seguem os rótulos da unidade: "Série" e "Bimestre" no colégio,
  "Semestre" e "Oferta" na faculdade.

## O que muda no código

| Área | Mudança |
| --- | --- |
| Identidade | `Identidade` ganha `unidades` (permitidas) e `unidade_ativa`; o `load_identity` confere o vínculo |
| Guards | `admin_required` passa a exigir unidade; nasce um helper único de escopo, e toda consulta raiz passa por ele |
| Consultas | As 49 consultas diretas e as listagens das telas da secretaria, acadêmico, frequência, estudos, cursos, solicitações e documentos |
| Cadastro | Aluno, professor e admin são criados **na unidade ativa**. Se a conta já existe na outra unidade (mesmo e-mail), o sistema só acrescenta o vínculo, sem mostrar nada dos dados da outra unidade |
| Telas | Seletor de unidade no topo; coluna Unidade na visão "Todas"; checklist "Primeiros passos" por unidade |
| Supremo | O diretório de pessoas passa a informar a unidade |
| Testes | Contratos de isolamento rota por rota (abaixo) e concorrência em PostgreSQL |

## Ordem das migrations

| Nº | Conteúdo | Situação |
| --- | --- | --- |
| **010** | Unidades: `unidades`, `usuario_unidades`, `unidade_id` nas 8 tabelas raiz, chaves compostas, Row-Level Security; os dados atuais vão para a unidade 1 | A propor depois deste estudo; só executada com revisão |
| 011 | Ofertas extras da B4, dentro da unidade de nível superior (era a proposta 010); `escola_termos` sai, porque os rótulos ficam na unidade | Modelo já aprovado em 24/11; proposta a renumerar |
| 012 | Passagem de ano ou de semestre, conforme a unidade | Em discussão |

## Contratos de teste (RED) a escrever

Na próxima etapa, eles serão escritos antes do código e falham até a implementação:

1. O admin do colégio não vê na lista nem abre (404) um aluno, uma turma, um professor, uma
   disciplina, uma solicitação ou um documento da faculdade, e vice-versa. Isso vale para
   **cada rota** da secretaria.
2. O admin do colégio não grava na faculdade: criar, matricular, atribuir, aprovar e
   arquivar respondem 404, e nada muda no banco.
3. O super admin vê as duas unidades na visão "Todas" e cria em qualquer uma.
4. Um professor com vínculo nas duas unidades faz login uma vez, troca de unidade e, em cada
   uma, vê só as turmas daquela unidade.
5. Trocar para uma unidade sem vínculo, inclusive forjando a sessão ou o ID, responde 403 e
   não muda a unidade ativa.
6. Revogar o vínculo derruba o acesso àquela unidade na requisição seguinte.
7. O banco recusa uma turma do colégio ligada a uma disciplina da faculdade (chave composta).
8. Com a Row-Level Security, uma consulta sem filtro feita como o admin do colégio não
   devolve linhas da faculdade (só PostgreSQL).
9. A instalação de uma unidade só continua igual, e a regressão atual passa sem mudanças de
   comportamento.
10. Cadastrar na faculdade um e-mail que já é aluno do colégio só acrescenta o vínculo, sem
    expor dados do colégio.

## Decisões pendentes (com recomendação)

| # | Decisão | Recomendação |
| --- | --- | --- |
| A | Uma pessoa pode ter **perfis diferentes** em cada unidade (admin no colégio, professor na faculdade)? | **Não nesta versão**: um perfil por conta, e quem tiver dois papéis usa duas contas. Perfil por unidade mexe no token e em todas as rotas, e pode vir depois |
| B | Aluno nas duas unidades: um cadastro só? | **Sim**: um cadastro (mesmo CPF), com o número de matrícula atual. Um RA próprio da faculdade, se for exigido, entra depois como campo do vínculo |
| C | Biblioteca de cursos | **Por unidade**, seguindo a disciplina do curso |
| D | Comunicados | **Por unidade**; o super admin pode enviar para todas |
| E | Identidade visual | **Uma da instituição** (mesmo endereço), com o nome da unidade no topo; os rótulos são por unidade |
| F | Visão "Todas" do super admin | **Leitura combinada** com a coluna Unidade; para criar, escolhe a unidade |
| G | Row-Level Security no PostgreSQL | **Sim**, nas tabelas raiz, como segunda barreira, além do filtro no código |

## Fora deste estudo

- Mais de uma instituição na mesma instalação: continua uma instalação por cliente.
- Perfis diferentes por unidade (decisão A).
- Graduação com matriz curricular, créditos e diploma (já estava fora da B4).
- Financeiro por unidade: entra no estudo do financeiro escolar.
