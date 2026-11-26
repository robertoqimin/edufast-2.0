# U4 — Primeiros passos e telas vazias com o próximo passo

Data: 25/11/2026. Branch `feature/melhoria-dezembro`, a partir do commit
«chore: adiciona demonstracao em camera lenta da U3 no Edge». Etapa U4 do
[plano de UX](../planejamento/PLANO_UX_2026-11-24.md) (objetivo O2). **Sem migration.**

## Resultado das metas

| Meta (O2) | Antes | Depois |
| --- | --- | --- |
| Guia de implantação | Nenhum: a ordem precisava ser conhecida de antemão | Checklist **"Primeiros passos"** na Visão geral da direção e da secretaria. São 8 passos obrigatórios e 1 opcional, cada um com progresso e o **próximo passo** destacado |
| Primeira tela da direção | "Usuários e permissões" | **Visão geral com o checklist** |
| Telas vazias com o próximo passo | **9 de 66** mensagens | **66 de 66**, medidas por teste em todos os templates da escola |
| Escola nova configurada só seguindo o guia | Não verificado | **Ensaio no Edge**: escola vazia, só com o acesso da direção, configurada clicando no botão do próximo passo, até "Implantação concluída". 25 verificações, nenhuma falha |

## O checklist

Os passos são calculados a partir dos dados que já existem; nada novo é gravado. Na ordem:

| Passo | Quem faz | Concluído quando | Leva a |
| --- | --- | --- | --- |
| 1. Calendário escolar do ano | Direção | existe calendário | Regras e identidade da escola |
| 2. Regras do boletim | Direção | existe regra de boletim | Regras e identidade da escola |
| 3. Contas da equipe | Direção | há conta ativa de secretaria e de professor | Usuários e permissões |
| 4. Disciplinas | Secretaria | há disciplina | Disciplinas |
| 5. Turmas do ano | Secretaria | há turma ativa (não arquivada) | Gestão acadêmica |
| 6. Disciplinas e professores de cada turma | Secretaria | **toda** turma ativa tem professor atribuído | Gestão acadêmica |
| 7. Alunos matriculados | Secretaria | **toda** turma ativa tem aluno | Gestão acadêmica |
| 8. Boletim aplicado às turmas | Direção | **toda** turma ativa tem a regra aplicada (períodos criados) | Regras e identidade da escola |
| Cursos liberados (opcional) | Secretaria | há liberação ativa | Cursos |

Como cada perfil vê o checklist:

- **Secretaria:** os passos da direção aparecem como "A cargo da direção", sem botão.
- **Sem turma ainda:** os passos que dependem dela mostram "Crie uma turma antes".
- **Implantação concluída:** o checklist fica recolhido ("Implantação concluída · 8 de 8") e cada
  passo ganha um botão "Revisar".

## Mudanças

- **`app/services/primeiros_passos.py`** (novo): o cálculo dos passos.
- **`admin_painel.html` migrado para o layout padrão** (`gestao_base`). Isso adianta uma das 12
  telas antigas da U5 (ficam 11).
  - Usa `stats-grid`, `stat-card` e tabela do protocolo.
  - Mantém os números (alunos, professores, matrículas pendentes e criadas hoje) e os últimos
    registros com "Gerenciar".
  - O título passou a ser "Visão geral", e o cumprimento diz qual perfil está logado (Direção
    ou Secretaria).
- **`home_routes.admin_dashboard`:** monta o checklist.
- **`login.js`:** a direção passa a entrar na Visão geral (`/admin/dashboard`).
- **50 mensagens de tela vazia reescritas em 25 templates.** Cada uma diz:
  - o que fazer ("Crie a primeira no formulário desta página", "Peça à secretaria para…"); ou
  - quem faz e quando o conteúdo aparece ("Os materiais aparecem aqui quando o professor
    publicar").

  Onde ajuda, há um link para Gestão acadêmica. A lista de professores vazia em Solicitações
  também ganhou acento ("disponível").
- **`escola.css`:** estilos do checklist com os tokens do protocolo, empilhamento no celular e
  `.sr-only` para o estado de cada passo ("Concluído." ou "Pendente.") ser lido por leitor de
  tela.
- **Auditoria de acessibilidade:** inclui a Visão geral da direção (80 páginas).
- **`scripts/ver-u4.cjs`** (novo): ensaio de aceite e demonstração em câmera lenta.

## Testes

| Verificação | Resultado |
| --- | --- |
| `test_u4_primeiros_passos.py` (novo, 5 testes): escola parcial com progresso e próximo passo; secretaria vê passos da direção sem link; escola completa recolhe o checklist; turma arquivada não conta e, sem turma, nada que depende dela aparece como feito; **toda tela vazia diz o próximo passo** (66 de 66) | OK |
| Suíte completa, SQLite | **386 OK** (43 pulados, só PostgreSQL) |
| Regressão em PostgreSQL 17 descartável, papel sem superusuário | **386 OK** (2 pulados); HTTP aprovado |
| Acessibilidade (axe-core) | **80 de 80** páginas |
| Ensaio de aceite no Edge (`ver-u4.cjs`, escola nova) | **25 de 25** |
| Edge — U3, U2b e U2 (regressão) | 18 de 18, 23 de 23, 44 de 44 |
| Demo completa | 44 de 44 |
| Protocolo de design | Aprovado |

O ensaio de aceite (`ver-u4.cjs`) funciona assim:

- recria a escola do ambiente de gravação vazia (`iniciar-educafast.ps1 -PrepararBancoNovo`)
  e cria o acesso da direção pelo comando oficial `create-admin --super-admin`;
- a cada passo, volta à Visão geral, confere "N de 8", confere que o passo destacado é o
  esperado e **clica no botão desse passo**, preenchendo a tela de destino.

O que ele percorre:

1. **Direção:** calendário, regras do boletim e contas (secretaria, professora e dois alunos).
2. **Secretaria:** vê "A cargo da direção" nos passos que não são dela e faz disciplina, turma,
   atribuição da professora e matrícula dos alunos.
3. **Direção:** aplica o boletim à turma.
4. **Resultado:** "Implantação concluída · 8 de 8".
5. **Celular:** o checklist sem rolagem horizontal.

Dois problemas apareceram no ensaio e foram corrigidos:

- **Primeira tela da direção:** o login a levava para "Usuários e permissões", e o checklist
  não era a primeira coisa que ela via. O ensaio agora confere que a direção entra na Visão
  geral.
- **Campo de nome do administrador:** o roteiro tentava preencher esse campo, oculto desde a
  U1, e esperava até esgotar o tempo. Era um problema do roteiro, não do sistema.

## Inspeção visual

Capturas em
[`docs/design/referencias/2026-11-25-u4-primeiros-passos/`](../design/referencias/2026-11-25-u4-primeiros-passos/),
4 imagens com manifesto:

- escola vazia vista pela direção;
- secretaria continuando a implantação;
- implantação concluída;
- checklist no celular.

Um ajuste foi feito durante a inspeção: com a implantação concluída, o texto "Siga a ordem"
passou a ser "Use “Revisar” para ajustar o que for preciso".

## Limitações e observações

- **Telas apontadas pelo checklist:** os passos 5 a 7 levam a "Gestão acadêmica", a tela com
  turma, atribuição e matrícula. A tela antiga "Turmas" continua existindo, e a unificação das
  duas é da U5.
- **Ordem dos passos:** os passos 6 e 7 mostram o botão mesmo antes de existir turma (com o
  aviso "Crie uma turma antes"). O checklist orienta a ordem, mas não bloqueia.
- **Validação com pessoas:** o teste com uma escola real, sem roteiro, fica para a validação
  com usuários (SUS) prevista no plano.

## Próxima etapa

U5 (O3): migrar as 11 telas antigas restantes para o layout padrão e unificar "Turmas" e
"Gestão acadêmica". Inclui o filtro pendentes/decididas e o nome do solicitante em
Solicitações.
