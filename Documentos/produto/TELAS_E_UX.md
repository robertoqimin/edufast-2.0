# Telas e experiência do usuário

[Início](../../README.md) · [Roadmap](../planejamento/ROADMAP.md)

## Direção do produto

Organizar a rotina escolar por tarefas: localizar uma turma, resolver uma pendência, lançar uma nota ou revisar uma jornada. O usuário deve entender onde está, qual informação está consultando e o resultado de cada ação.

A referência funcional é o [protocolo original](../PROTOCOLO_DESIGN.md), recuperado
de `Samucau1/Projeto-Educa-Fast`. Usa DM Sans local, tokens compartilhados, menu e
barra superior próprios. O padrão é escuro/ciano; o superperfil configura nome,
marca, paleta clara/escura, fonte, espaçamento e bordas com validação de contraste.
Os SVGs em `Protótipo/edufast` são pranchas conceituais distintas, e não substituem
esse design. Login, painéis, superperfil e solicitações usam a identidade original.

## Telas existentes no código

| Tela | Rota de consulta | Template |
| --- | --- | --- |
| Entrada e login | `/` para visitante; envio do login em `POST /login` | `login.html` |
| Painel administrativo | `/admin/dashboard` | `admin_painel.html` |
| Cadastro de alunos | `/admin/cadastro-alunos` | `admin_cadastro_aluno.html` |
| Cadastro de professores | `/admin/cadastro-professores` | `admin_cadastro_professores.html` |
| Consulta de cadastros | `/admin/banco-de-dados` | `admin_banco_dados.html` |
| Detalhes do aluno | `/admin/alunos/<id>` | `admin_detalhes_aluno.html` |
| Detalhes do professor | `/admin/professores/<id>` | `admin_detalhes_professor.html` |
| Turmas | `/admin/turmas` | `admin_turmas.html` |
| Disciplinas | `/admin/disciplinas` | `admin_disciplinas.html` |
| Comunicados | `/admin/comunicados` | `admin_comunicados.html` |
| Área do professor | `/professor/dashboard` | `professor_painel.html` |
| Área do aluno | `/aluno/dashboard` | `aluno_painel.html` |
| Disciplina do aluno | `/aluno/disciplinas/<id>` | `aluno_disciplina.html` |

As rotas protegidas exigem o perfil correspondente. Os templates estão em `Codigos/app/templates/`. O catálogo foi conferido no código, sem declarar teste de navegação de todos os fluxos.

## Protótipos de apresentação

| Prévia | Objetivo | Interação a implementar |
| --- | --- | --- |
| [Painel](../../Protótipo/edufast/painel.svg) | Dar contexto da rotina e das pendências | Abrir pendência ou módulo com filtro aplicado |
| [Turmas](../../Protótipo/edufast/turmas.svg) | Localizar turmas e consultar sua composição | Buscar, filtrar e abrir detalhe com alunos e docentes |
| [Ponto](../../Protótipo/edufast/ponto.svg) | Revisar jornadas e exceções | Consultar marcações, justificar e aprovar ajustes |
| [Pagamentos](../../Protótipo/edufast/pagamentos.svg) | Visualizar obrigações por competência | Separar folha e financeiro, revisar e consultar histórico |

Os nomes, totais e valores são fictícios. Indicadores não são métricas reais da escola ou desempenho medido do produto.

## Novas telas propostas

| Área | Telas | Dependências |
| --- | --- | --- |
| Pessoas | Lista de colaboradores, ficha, cargo e contrato | Modelo de RH e permissão específica |
| Ponto | Meu ponto, espelho mensal, justificativas e fila de aprovação | Jornada, marcações e auditoria |
| Folha | Competências, eventos, demonstrativo e fechamento | Contratos e ponto aprovado |
| Financeiro | Contas a pagar/receber, mensalidades e conciliação | Títulos, parcelas e confirmação de transações |
| Cursos | Biblioteca, editor de conteúdo, player e progresso | Oferta por turma e autorização de conteúdo |
| Gestão | Relatórios e visão por unidade | Dados consistentes e escopo por instituição |

Não atribuir rotas públicas a essas telas até existir implementação e controle de acesso.

## Critérios de UX/UI para implementação

1. **Orientação:** título claro, contexto de turma/período e navegação com item ativo.
2. **Agilidade:** busca e filtros persistentes durante o fluxo; atalhos para ações frequentes.
3. **Formulários:** rótulos visíveis, erros próximos ao campo e preservação do preenchimento após falha.
4. **Feedback:** mostrar estados carregando, vazio, falha, sucesso e acesso negado; evitar tabelas vazias sem explicação.
5. **Ações sensíveis:** revisar antes de fechar folha, aprovar ajustes ou confirmar pagamentos. Nunca exibir sucesso antes da confirmação do servidor.
6. **Acessibilidade:** navegação por teclado, foco visível, contraste verificado e estados descritos por texto, além de cor.
7. **Responsividade:** menu adaptável, cartões em coluna e tabelas navegáveis em telas pequenas sem perder ações.
8. **Consistência:** componentes compartilhados para botões, campos, filtros, cartões, tabelas e mensagens.

As pranchas ainda não demonstram todos esses estados; são critérios para a interface funcional.

## Validação com usuários

Avaliar com secretaria, professores, alunos e, nos módulos futuros, RH/financeiro. Observar se conseguem localizar uma turma, cadastrar um aluno e consultar uma pendência sem ajuda. Registrar tempo por tarefa, taxa de conclusão, erros e percepção de facilidade antes e depois da mudança. Definir metas após obter uma linha de base; não publicar percentuais de melhoria sem medição.
