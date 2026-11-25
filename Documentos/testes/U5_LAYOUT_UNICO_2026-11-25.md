# U5 — Uma aparência e um caminho por tarefa

Data: 25/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«feat: guia a implantacao com checklist e telas vazias com proximo passo (U4)». Etapa U5 do
[plano de UX](../planejamento/PLANO_UX_2026-11-24.md) (objetivo O3). **Sem migration.** A pedido do
usuário, U4 e U5 foram testadas juntas no Edge.

## Resultado das metas

| Meta (O3) | Antes | Depois |
| --- | --- | --- |
| Telas no layout padrão | 48 de 59 (11 telas antigas após a U4) | **58 de 58**: 55 estendem `gestao_base`; o login (tela pública) e Usuários e permissões (tela de referência do design system) têm estrutura própria com o cabeçalho padrão, como o protocolo permite. A tela antiga de Turmas foi aposentada (59 → 58) |
| Telas de turma | **Duas** ("Turmas" e "Gestão acadêmica"), com regras diferentes; a diferença já tinha causado o defeito de matrícula de 24/11 | **Uma** ("Turmas"): criar a turma (com turno), registrar matéria com ou sem professor, retirar matéria sem histórico, matricular e desmatricular, arquivar. O endereço antigo redireciona para ela, e envios antigos recebem 410 com a orientação |
| Tarefa com dois caminhos | Turma, matéria, professor e matrícula tinham dois caminhos de gravação | **Nenhum**: um caminho por tarefa; registrar e retirar matéria usam as mesmas funções de matrícula (`matriculas.py`) |
| Solicitações | Lista única com até 100 itens, inclusive os decididos, e o solicitante mostrado pelo número | Filtro **Pendentes / Decididas / Todas** com contagens (abre em Pendentes), **nome e perfil** de quem enviou e de quem decidiu, e a data da decisão |

## Mudanças

### Telas migradas para o layout padrão (10)

As telas migradas são: Registros acadêmicos, Cadastro de alunos, Cadastro de professores,
Comunicados, Detalhes do aluno, Detalhes do professor, Disciplinas, Painel do aluno, Disciplina
do aluno e Painel do professor.

- **Renderização no servidor:** sai o `<template>` montado por JavaScript. O menu, a barra
  superior e os avisos vêm do `gestao_base`.
- **Cabeçalho padrão** (`page-heading`) com etiqueta, título e texto, sem o selo falso "Admin
  Secretaria · Online agora" e sem os círculos de avatar decorativos. Os botões reais do
  cabeçalho (Limpar e Salvar registro nos cadastros) e a foto real do aluno ou professor
  continuam.
- **Título da página:** a barra superior mostrava "Educa Fast" no lugar do título; agora mostra
  o título real. O nome padrão do produto passou a "EduFast".
- **CSS próprio e `utilities.css`:** continuam carregados, **antes** do design system,
  reproduzindo a ordem antiga. Assim o conteúdo não muda e o design system tem a última
  palavra. A primeira tentativa os carregava depois, e o reset do `utilities.css` apagou os
  títulos; isso foi visto na inspeção e corrigido.
- **`shell_react.js`:** sem `<template>` para montar, liga as abas e dispara o mesmo evento de
  montagem sobre a página. Assim os scripts antigos (abas, busca dos registros, cadastro via
  formulário) funcionam sem mudança.
- **Arquivos removidos:** o bloco `head` no `gestao_base` recebe o CSS da página. Saíram o
  `painel.css` (fundo azul e cartões de vidro) e o `react_runtime.html`, que ficaram sem uso.
- **Removido o botão "Exportar CSV"** de Registros acadêmicos: ele não tinha nenhuma ação.
- **Corrigida a "Dica de Gestão"** do cadastro de alunos, que prometia um e-mail automático
  inexistente. Agora ela diz o próximo passo real: matricular na turma e entregar o acesso.

### Uma tela de turma

- **`curso_turmas.html`** (agora "Turmas"):
  - turno na criação e na edição;
  - formulário "Matéria e professor" com a opção "Ainda sem professor";
  - por turma: matérias com os professores (revogar), "Retirar matéria" quando não há
    professor, alunos matriculados com link para o detalhe, dados da turma e arquivar.
- **`curso_routes.gestao_turmas`:**
  - `turno`;
  - código repetido responde 409;
  - `atribuir` sem professor registra a matéria (`matriculas.registrar_disciplina`);
  - `retirar_materia` usa `historico_da_disciplina` e `retirar_disciplina`;
  - matrícula repetida responde 409.
- **`cursos.atribuir`:** usa `insert_if_missing`. A restrição única arbitra atribuições
  simultâneas, e dois professores atribuídos ao mesmo tempo à mesma matéria terminam os dois
  com sucesso, como na tela antiga.
- **`/admin/turmas`:** GET → 301 para a tela única; POST → 410 "Esta tela foi unificada em
  Turmas…". `admin_turmas.html` e `admin_turmas.css` foram removidos.
- **Menu:** uma entrada "Turmas" em Organização da escola; sai "Gestão acadêmica".
- **Textos atualizados:** checklist da U4, telas vazias e o roteiro de gravação (`demo_video.cjs`)
  já apontam para a tela única.
- **Funções antigas de serviço:** `associar_aluno_turma` e as demais não têm mais rota. Ficam só
  sob os testes de caracterização.

### Solicitações

- **`aprovacoes_routes`:**
  - `?estado=pendentes|decididas|todas`;
  - contagens com a mesma visibilidade da lista;
  - `_nomes` resolve professor e aluno pelo nome do cadastro e as demais contas pelo e-mail, com
    o perfil.
- **`solicitacoes.html`:**
  - filtro com `aria-current`;
  - "Enviada por", "Decidida por … em …";
  - título com acento;
  - tela vazia por filtro.

## Testes

| Verificação | Resultado |
| --- | --- |
| `test_u5_layout_unico.py` (novo, 6 testes): todas as telas no padrão (lista fechada das 3 exceções); sem `<template>` nem selo falso; uma entrada de turma no menu; telas migradas abrem com menu, título e cabeçalho padrão; Turmas mostra matérias, professores e alunos; Solicitações filtra e mostra nomes | OK |
| Testes migrados para a tela única: `test_turma_materia` (11), `test_matriculas_disciplinas`, `test_application`, `test_concurrency` (concorrência real só em PostgreSQL), contrato B4 | OK, com os contratos mantidos (ver abaixo) |
| Suíte completa, SQLite | **393 OK** (43 pulados, só PostgreSQL) |
| Regressão em PostgreSQL 17 descartável, papel sem superusuário, com concorrência real | **393 OK** (2 pulados) na segunda rodada, após a correção abaixo; HTTP aprovado |
| Acessibilidade (axe-core) | **84 de 84** páginas (entraram Cadastro de professores, Comunicados e Detalhes do professor) |
| **U4 + U5 juntas no Edge** (`ver-u4-u5.cjs`, escola nova) | **48 de 48** |
| Edge — U2, U2b e U3 (regressão) | 44 de 44, 23 de 23, 18 de 18 |
| Demo completa | 44 de 44 |
| Protocolo de design | Aprovado |

### U4 + U5 juntas no Edge (pedido do usuário)

`node scripts/ver-u4-u5.cjs` parte de uma escola **vazia**, só com o acesso da direção, e
percorre:

1. **U4:** a escola é configurada seguindo só o checklist, até "Implantação concluída · 8 de
   8" (25 verificações).
2. **U5 na mesma escola** (23 verificações):
   - **Tela única de Turmas:**
     - Disciplinas no layout padrão;
     - o menu "Turmas" leva à tela única;
     - Ciências registrada "Ainda sem professor" e depois retirada;
     - a turma mostra Matemática com a professora e os alunos;
     - o endereço antigo `/admin/turmas` redireciona.
   - **Telas migradas** (Alunos, Professores, Registros e Comunicados):
     - todas com o cabeçalho padrão e sem o selo falso;
     - a busca dos registros continua funcionando.
   - **Professora:**
     - o painel abre no layout padrão;
     - as abas funcionam;
     - ela envia um aviso.
   - **Secretaria em Solicitações:**
     - o filtro abre em "Pendentes (1)";
     - aparece "Enviada por: Marina Costa (professor)";
     - ela aprova o aviso;
     - em Decididas aparece "Decidida por … em …".
   - **Aluno:** o painel abre no layout padrão, com Matemática e a professora.

Capturas:

- [`2026-11-25-u4-u5-juntas/`](../design/referencias/2026-11-25-u4-u5-juntas/): 7 imagens.
- Comparação antes/depois das telas migradas:
  [`2026-11-25-u5-antes/`](../design/referencias/2026-11-25-u5-antes/) (26) e
  [`2026-11-25-u5-depois/`](../design/referencias/2026-11-25-u5-depois/) (24), desktop e
  celular, cada pasta com manifesto. A tela antiga de Turmas só existe em "antes".

Contratos dos testes migrados:

- **Mantidos, agora na tela única:**
  - registrar a matéria matricula a turma inteira;
  - quem entra depois herda as matérias;
  - registro repetido, matéria inexistente, campo faltando e turma arquivada são recusados;
  - só a secretaria registra (o envio do professor cai no fluxo de aprovação e é recusado, sem
    efeito);
  - retirar preserva a matéria cursada em outra turma;
  - matéria com histórico não sai;
  - criação de turma duplicada e corridas de criação, matrícula e atribuição.
- **Substituídos:** os testes do fluxo antigo "associar professor à turma" (sem matéria) deram
  lugar à atribuição explícita turma + matéria + professor (professor inexistente → 404).
- **Novos:**
  - a tela antiga redireciona e recusa envios (410);
  - turno na criação e na edição;
  - código repetido → 409.

## Achado da regressão em PostgreSQL

Na primeira rodada em PostgreSQL, o teste de concorrência real de "dois professores atribuídos
ao mesmo tempo na mesma turma" respondeu **302 e 409** (esperado: 302 e 302).

- **Causa:** a atribuição marcava a turma como "gestão explícita" consultando e depois
  inserindo o registro de adoção (`turma_estados`). Com duas requisições ao mesmo tempo, as duas
  tentavam inserir.
- **Desde quando:** o risco já existia na Gestão acadêmica antes da U5. Só não era testado,
  porque o teste usava a tela antiga.
- **Correção:** `insert_if_missing` também na adoção (atribuir e "adotar"). A restrição única
  arbitra e as duas atribuições terminam com sucesso.
- **Validação:** o SQLite não reproduz essa corrida, por isso a confirmação foi a segunda
  rodada em PostgreSQL.

## Limitações e observações

- **Classes antigas:** o conteúdo interno das 10 telas migradas ainda usa as classes de antes
  (`glass-card`, utilitários), restilizadas pelo `app.css` com os tokens. Trocar classe por
  classe pelos componentes do protocolo fica para quando cada tela for revisitada.
- **Contagem das Solicitações:** conta as últimas 100 solicitações visíveis, o mesmo limite da
  lista.

## Próximo passo

Plano de UX concluído (U1–U5 e U2b). O plano prevê a **validação com pessoas**: teste de
usabilidade com 5 pessoas por perfil (secretaria, professor e aluno), nas jornadas do roteiro do
vídeo, medindo conclusão das tarefas, tempo e o questionário **SUS**, com meta de 80 ou mais.
