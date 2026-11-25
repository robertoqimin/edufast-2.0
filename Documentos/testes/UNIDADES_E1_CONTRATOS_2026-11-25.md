# Unidades — etapa 1: decisões e contratos de isolamento

Data: 25/11/2026. Branch `feature/melhoria-dezembro`. Primeira etapa do
[estudo das unidades](../planejamento/ESTUDO_UNIDADES_2026-11-25.md) (colégio e faculdade na
mesma instalação). **Sem migration e sem mudança no código da aplicação.**

O usuário pediu para fazer todas as etapas, mas consultá-lo ao fim de cada uma.

## Decisões registradas

- **Estrutura:**
  - uma instalação com unidades;
  - um login, com troca de unidade;
  - um endereço só.
- **Recomendações A a G aprovadas:**
  - um perfil por conta;
  - um cadastro por aluno;
  - biblioteca de cursos por unidade;
  - comunicados por unidade, e o super admin pode enviar para todas;
  - identidade visual única, da instituição;
  - visão "Todas" do super admin para leitura, escolhendo a unidade antes de criar;
  - Row-Level Security nas tabelas raiz.
- **Adendo do usuário à decisão B:** o aluno que termina o 3º ano do colégio pode **subir o
  perfil para a faculdade** com o histórico escolar e todos os documentos. O estudo detalha a
  regra:
  - só a unidade de origem libera;
  - a passagem mantém o mesmo login;
  - o histórico e os documentos ficam só para leitura na faculdade;
  - a passagem fica registrada e não se repete;
  - ela não matricula o aluno sozinha em nenhuma turma.

## Contratos (RED)

O arquivo [`test_contratos_unidades.py`](../../.github/cicd/tests/unidades/test_contratos_unidades.py)
tem 14 contratos:

| # | Contrato |
| --- | --- |
| 1–2 | As listas de cada secretaria (Turmas, Disciplinas, Visão geral, Alunos, Solicitações e busca de alunos) não mostram a outra unidade |
| 3 | Aluno, professor ou boletim de outra unidade responde 404 |
| 4 | Matricular, arquivar e editar na outra unidade respondem 404, e nada muda |
| 5 | O super admin vê as duas unidades e precisa escolher a unidade para criar |
| 6 | O professor das duas unidades troca de unidade e vê só as turmas da unidade ativa |
| 7 | Trocar para uma unidade sem vínculo, ou para "Todas" sem ser super admin, responde 403. A sessão adulterada é recusada |
| 8 | Revogar o vínculo derruba o acesso na requisição seguinte |
| 9 | O banco recusa turma e disciplina de unidades diferentes e aluno sem vínculo numa turma da unidade |
| 10 | Row-Level Security: uma consulta sem filtro não devolve a outra unidade (só PostgreSQL) |
| 11 | Cadastrar um e-mail que já existe na outra unidade só cria o vínculo, sem conta nova e sem expor dados |
| 12–14 | Adendo: a passagem para a faculdade leva o histórico e os documentos; só a origem libera; fica registrada e não se repete |

## Execução

| Verificação | Resultado |
| --- | --- |
| Contratos, SQLite | **13 erros e 1 pulado**, como esperado. Todos falham porque `UnidadeModel` ainda não existe, e o contrato 10 só roda em PostgreSQL |
| Regressão | Continua com **393** testes. A pasta `unidades/` não é pacote e fica fora da regressão, como a `b4_superior/` |

A suíte completa não foi rodada de novo: esta etapa não muda o código da aplicação.

## Próxima etapa (depende do usuário)

**Etapa 2:** propor a migration 010, com as unidades, os vínculos, a coluna `unidade_id` nas
8 tabelas raiz, as chaves compostas, a tabela de passagens e a Row-Level Security. Ela será
apresentada com uma ficha de riscos e de como desfazer. Pela regra do projeto, só é executada
depois da revisão do usuário.
