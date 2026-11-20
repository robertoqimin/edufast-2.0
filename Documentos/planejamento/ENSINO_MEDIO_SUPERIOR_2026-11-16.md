# Primeira versão — ensino médio e superior

Direção definida pelo usuário em 16/11/2026. Complementa o
[plano de preparação comercial](PREPARACAO_ENTREGA_2026-11-16.md).
Objetivo atual: desenvolver e demonstrar um produto para venda; contratar servidor
e implantar quando houver cliente. "Produção hoje" significa iniciar o desenvolvimento.

## 1. Escopo confirmado e limites da primeira versão

Públicos: ensino médio e ensino superior. Prioridades: usabilidade, agilidade,
baixo consumo de hardware e rotina básica de ensino. A visão é atender ambos;
a primeira versão cobre os fluxos descritos aqui, sem declarar cobertura de todas
as obrigações administrativas desses segmentos.

| Área | Entrega da primeira versão | Critério de uso |
| --- | --- | --- |
| Turmas e disciplinas | Consultar turmas, disciplinas, professores e alunos vinculados | Cada perfil encontra somente o que lhe é autorizado; turma e período ficam claros |
| Chamada e presença | Professor registra e confirma diretamente a chamada da própria oferta | Elenco completo, sem presença presumida; relatório atualizado após confirmação; revisão preserva histórico |
| Espaço da disciplina | Avisos, materiais de estudo e seções organizadas pelo professor | Aluno encontra conteúdo da turma/disciplina correta; seções têm nome, ordem e estado explícitos |
| Autoria docente | Criar capítulos, conteúdo e abas dentro de suas disciplinas autorizadas | Não permite editar disciplina de outro professor nem conceder matrícula/permissão |
| Cursos de aprendizagem | Biblioteca → curso → módulos → capítulos/aulas → progresso | Professor organiza sequência; aluno acessa oferta liberada e retoma sua aula |
| Acesso e gestão básica | Contas, vínculos, comunicação, documentos e gestão dos conteúdos | Administração configura a instituição; acesso e arquivos preservam autorização |

**Decisão expressa sobre frequência:** o professor confirma diretamente; substitui
a exigência anterior de aprovação administrativa para novas chamadas. Esta é uma
mudança implementada no lote MS01, validada em SQLite/HTTP/navegador e, no CI
de 19/11, também em MySQL. Isso não ativa esquemas persistentes nem constitui
aceite comercial completo. Não
aprovar automaticamente chamadas antigas pendentes. Atestados continuam sob análise
administrativa; falta justificada continua sendo falta, sem converter em presença.

A autonomia para organizar materiais foi solicitada. O código atual intercepta
operações docentes de cursos e as transforma em propostas. Separar na implementação
a edição de rascunhos e organização das seções das regras de publicação já existentes.
A decisão de frequência não autoriza alterar aprovação de notas ou outras operações.
Caso a publicação de cursos continue exigindo revisão, o fluxo deve explicar esse
estado; não apresentar um rascunho docente como conteúdo já disponível aos alunos.

Alura e EBAC são referências conceituais trazidas pelo usuário para organização de
aprendizagem: módulos, sequência e retomada. Não houve análise dessas plataformas
nesta tarefa; suas funcionalidades não são requisitos presumidos. Preservar o design
EducaFast e adaptar a experiência aos componentes existentes.

## 2. Organização do produto

Fluxo escolar: **instituição → período letivo → turma/oferta de disciplina → alunos e professor**.
Fluxo de aprendizagem: **curso de aprendizagem → módulos → capítulos/temas → aulas e materiais**.

"Curso de graduação" é uma organização acadêmica institucional; "curso de
aprendizagem" é a sequência de conteúdo. Não reutilizar automaticamente a tabela
`cursos` para representar graduação, matriz curricular ou diploma.

| Contexto | Ensino médio | Ensino superior | Diretriz |
| --- | --- | --- | --- |
| Organização | Série/ano, turma e disciplinas | Curso de graduação, semestre/período e ofertas de disciplinas | Configurar termos e regras; não duplicar a aplicação |
| Matrícula | Rotina por turma, respeitando vínculos | Pode exigir matrícula individual por disciplina | Validar vínculo de acesso; não presumir que turma libera qualquer matéria |
| Calendário | Períodos definidos pela escola | Períodos definidos pela instituição | Reutilizar políticas existentes; não fixar bimestre ou semestre no código |
| Conteúdo | Material por disciplina e turma | Material por oferta de disciplina e período | Conteúdo reutilizável; acesso e progresso vinculados à oferta |

Matrícula por disciplina e estrutura de graduação precisam de verificação de modelo
antes de anunciar suporte completo ao superior. Pré-requisitos, créditos, equivalência,
transferência, diploma, integrações oficiais, RH, folha e financeiro escolar completo
são evolução futura, não itens concluídos desta primeira entrega.

### Espaço da disciplina e abas

- Seções iniciais propostas: **Avisos**, **Materiais de estudo** e **Cursos**.
- Professor pode criar, nomear, ordenar e arquivar seções da oferta autorizada.
  Arquivamento deve preservar conteúdo e referências históricas.
- Tipos iniciais propostos: aviso em texto, material em arquivo/link e acesso ao curso.
  Abas são conteúdo estruturado; não aceitam código, CSS ou scripts arbitrários.
- Rascunho não é visível ao aluno. A publicação respeita a política vigente até
  existir mudança específica implementada e testada para autoria/publicação.
- Arquivos de estudo usam autorização própria. Não reutilizar downloads de
  documentos pessoais/atestados como biblioteca pública de materiais.

### Cursos modulares

O código já tem `CursoModel`, `CapituloModel`, `TemaModel`, `AulaModel`, ofertas e
progresso. Antes de criar tabelas novas, conciliar esses níveis com os nomes de
módulo/capítulo na interface. Não renomear ou converter dados históricos silenciosamente.
Aula atualmente exige vídeo do YouTube; aulas somente em texto/arquivo são lacunas
a tratar com contrato e proposta de esquema revisável, se necessária.

Prever sequência, indicação da aula atual, anterior/próxima e conclusão explícita.
Progresso de conteúdo não equivale a presença em chamada, nota ou certificação.

## 3. Entregas e testes

| Ordem / ID | Implementação | Testes de aceite | Situação inicial |
| --- | --- | --- | --- |
| 0 / MS00 | Leitura eficiente da estrutura modular existente | Ordenação, grupos vazios, curso isolado, duplicação e consultas sem crescimento por capítulo/tema | Implementada e validada em SQLite; [evidência e limites](../testes/CURSOS_ESTRUTURA_2026-11-16.md) |
| 1 / MS01 | Confirmar chamada diretamente pelo professor; consultar turma e elenco | Professor autorizado confirma; outro professor/aluno não grava; repetição não duplica; correção versionada preserva histórico; relatório reflete a confirmação | Implementada; SQLite/MySQL/HTTP aprovados no CI de 19/11; [evidências de implementação](../testes/CHAMADA_DIRETA_2026-11-16.md) |
| 2 / MS02 | Espaço da disciplina com Avisos e Materiais | Criar/editar conteúdo; aluno da oferta lê; outro aluno não acessa arquivo; campos escapados; erros não perdem o conteúdo persistido | Implementado; SQLite/MySQL/HTTP aprovados no CI de 19/11; [proposta 005 e limites](../testes/ESPACO_DISCIPLINA_2026-11-16.md); ativação persistente pendente de revisão |
| 3 / MS03 | Abas configuráveis com autonomia docente de organização | Criar, renomear, ordenar e arquivar; negar recurso alheio; rejeitar versão antiga; distinguir rascunho/publicação | Implementado; SQLite/MySQL/HTTP aprovados no CI de 19/11; [proposta 006 e limites](../testes/ABAS_DISCIPLINA_2026-11-19.md); ativação persistente pendente de revisão |
| 4 / MS04 | Consolidar cursos em módulos/capítulos/aulas e materiais | Professor organiza; aluno acessa oferta liberada, navega e retoma; edição preserva progresso e versão publicada | [Backend/API](../testes/API_CURSOS_MS04_2026-11-20.md) e [frontend com demo ENEM para teste manual](../testes/FRONTEND_CURSOS_MS04_2026-11-20.md) implementados localmente; revisão/ativação persistente da proposta 007 e aceite manual pendentes |
| 5 / MS05 | Revisar usabilidade e desempenho dos fluxos completos | Desktop/mobile, teclado, erros/vazios, jornada por perfil, tamanhos de assets, consultas, memória e tempos | A fazer |

Cada entrega funcional inclui backend, interface, testes de permissão/transação e
inspeção visual quando houver mudança de tela. Não acumular toda validação para MS05.
Migrations podem ser propostas; executar somente após revisão do usuário conforme AGENTS.md.

Atualização de evidências em 19/11: o commit `aedf8ad` passou no
[CI completo SQLite/MySQL](https://github.com/Samucau1/edufast-2.0/actions/runs/44552908275)
e no [piloto com APIs e central MySQL](https://github.com/Samucau1/edufast-2.0/actions/runs/44552900401).
Os relatórios anteriores mantêm suas limitações históricas; as execuções de 19/11
não são validação de funcionalidades futuras MS04/MS05 nem de ativação persistente.

Ordem de trabalho proposta: hoje fechar contratos e iniciar MS00/MS01; em seguida
concluir MS01 antes de MS02/MS03; consolidar MS04 e as jornadas com MS05. A agenda
de 16 a 20/11 é uma organização de trabalho, sem promessa de concluir tudo na semana.

## 4. Leveza como critério verificável

Reutilizar HTML/Jinja e componentes locais. JavaScript só onde ajuda a tarefa;
paginar listas no servidor; não carregar todos os arquivos/aulas ou vídeos na entrada.
Carregar vídeo sob demanda deve ser parte da revisão da experiência de estudo.
Não adicionar serviços ou bibliotecas pesadas sem medir a necessidade.

O [plano de desempenho](DESEMPENHO.md) contém metas provisórias. Medir antes de
transformá-las em promessa: recursos transferidos, consultas, CPU/RAM, tempo de
resposta e experiência em computador/celular modestos. Registrar ambiente e massa.
A otimização de consultas MS00 não comprova sozinha latência, memória ou capacidade.

## 5. Primeiro cenário demonstrável

Usar dados fictícios para uma turma do ensino médio e uma oferta do ensino superior.
Admin configura vínculos → professor confere elenco → confirma chamada → publica
aviso/material conforme regras → organiza curso → aluno encontra a disciplina,
consulta materiais, acompanha presença e retoma aula. Registrar as diferenças de
matrícula e período; não contorná-las com permissões mais amplas.

Concluir um lote quando a jornada correspondente funcionar, testes pertinentes
passarem e as limitações estiverem registradas. A primeira demonstração deve deixar
explícito quais lotes já estão concluídos.
