# Turma registrada na matéria — 24/11/2026

Base: commit «docs: registra validacao da demonstracao de gravacao (16,4 min)», branch
`feature/melhoria-dezembro`. Pedido do usuário depois da gravação do vídeo.

## Pedido

Hoje a matéria só chegava à turma de forma indireta: ao associar um professor, **todas** as
matérias dele eram puxadas para a turma. Não havia como dizer "esta turma cursa estas
matérias". O usuário pediu que a **turma inteira** seja registrada na matéria e que, com isso,
todos os alunos da turma passem a cursá-la na hora. Objetivo: quando a turma (o código dela)
passar para o próximo ano, ficar simples incluir novas matérias, professores e cursos.

## O que mudou

**Tela Turmas (`/admin/turmas`), nova seção "Registrar Turma na Matéria"**

- A secretaria escolhe turma e matéria. Todos os alunos da turma entram na matéria de uma vez.
- Aluno associado à turma depois herda **todas** as matérias dela (regra que já existia desde
  o commit «fix: matricula alunos nas disciplinas da turma e prepara ambiente de gravacao»,
  agora com o vínculo turma × matéria criado diretamente).
- A lista **Matérias por Turma** mostra quantos alunos cada uma tem e permite **Retirar** a
  matéria da turma.
- Recusas com mensagem: turma já registrada na matéria, turma arquivada, matéria inexistente,
  campos vazios.

**Retirar matéria da turma**

- Só é permitido enquanto a matéria não tiver histórico na turma: avaliações/notas, chamadas,
  materiais ou abas do Espaço da disciplina, cursos ofertados ou professor atribuído pela
  Gestão acadêmica. Com histórico, a retirada é recusada e nada é apagado.
- Os alunos da turma perdem a matéria, **exceto** quem a cursa também por outra turma.

**Associar professor à turma** (mudança de comportamento)

| Situação da turma | Antes | Agora |
| --- | --- | --- |
| Ainda sem matérias | Puxava todas as matérias do professor | Igual (fluxo antigo preservado) |
| Já tem matérias, professor leciona alguma delas | Puxava também as outras matérias dele | Liga o professor só às matérias da turma; nenhuma matéria nova é criada |
| Já tem matérias, professor não leciona nenhuma | Puxava as matérias dele | Recusa: "registre antes a turma na matéria dele" |

Motivo: com a matrícula automática, puxar uma matéria a mais colocaria a turma inteira nela.

**Sem migration.** A tabela `turmas_disciplinas` já existia; nada no banco foi alterado.

Arquivos: `app/services/matriculas.py` (registrar, verificar histórico, retirar),
`app/services/academico_service.py`, `app/controllers/admin_controller.py`,
`app/routes/home_routes.py`, `app/repositories/academico_repository.py`,
`app/presenters/admin_presenter.py`, `app/templates/admin_turmas.html`,
`app/static/css/admin_turmas.css`.

## Testes

Novo arquivo `.github/cicd/tests/test_turma_materia.py`, 10 casos:

1. registrar a turma matricula todos os alunos de uma vez (e a tela mostra "2 alunos");
2. aluno que entra depois herda todas as matérias da turma;
3. registro repetido, turma arquivada, matéria inexistente e campos vazios são recusados;
4. só a administração registra (aluno e professor são barrados);
5. professor em turma com matérias não traz as outras matérias dele;
6. professor sem nenhuma matéria da turma é recusado e não fica ligado à turma;
7. turma sem matérias mantém o fluxo antigo do professor;
8. retirar a matéria preserva quem a cursa por outra turma;
9. matéria com avaliação lançada não é retirada;
10. aluno da turma registrada vê a matéria no Espaço da disciplina.

Contra o código anterior, 8 dos 10 falham; os casos 4 e 7 são guardas de regressão e passam
nas duas versões, como esperado. `test_admin_characterization` foi atualizado: a página de
turmas agora também entrega a lista de matérias.

| Execução | Resultado |
| --- | --- |
| Rodada focada em container (SQLite descartável): `test_turma_materia`, `test_matriculas_disciplinas`, `test_admin_characterization` | 20 aprovados |
| `run_cursos_backend.py --suite regressao` — SQLite | 343 aprovados, 43 pulados (os mesmos de antes) |
| idem — PostgreSQL + concorrência real | 343 aprovados, 2 pulados |
| idem — HTTP real | 117 verificações aprovadas |
| idem — fonte inalterado durante a execução | Sim; containers removidos ao final |
| `verificar_protocolo_design.py` | Aprovado |

Uma primeira rodada da regressão foi **interrompida** por mim: removi um import que ficou sem
uso enquanto ela rodava, o que invalidaria a conferência de fonte inalterado. A árvore de
processos e os containers dela foram encerrados e a regressão foi refeita do zero sobre o
código final. Os resultados acima são só dessa segunda rodada.

## Inspeção visual

Servidor descartável (fixture sintética `teste01`, SQLite temporário, porta 5097), Edge via
Playwright. Capturas em
[`design/referencias/2026-11-24-turma-materia/`](../design/referencias/2026-11-24-turma-materia/COMPARACAO.md),
com manifesto.

- Desktop 1440×1000 e celular 390×844: sem rolagem horizontal (largura da página igual à da
  janela), sem cortes; no celular, cada item da lista quebra em duas linhas.
- Caminho completo pela interface: criar turma "2º ano A" → registrar em Matemática ("0
  alunos") → associar um aluno ("1 aluno") → retirar Matemática. Conferido no banco: a turma
  ficou sem a matéria e o aluno **manteve** Matemática, porque também está na turma original,
  que a oferece.
- Mensagem de recusa exibida ao repetir o registro: "Esta turma ja esta registrada nesta materia".

## Limitações e pendências

- A tela de Turmas é um modelo legado com estilos próprios (`admin_turmas.css`); a nova seção
  segue esse padrão local em vez dos componentes `course-*` do protocolo, para não destoar.
- As mensagens dessa tela antiga continuam sem acentos (padrão já existente nela) e aparecem
  no cartão "Nova Turma", no topo da página.
- A tela "Gestão acadêmica" (`/admin/gestao-turmas`) não ganhou o formulário novo; nela a
  matéria entra pela atribuição professor × turma × matéria, que já matricula os alunos.
- **Passagem da turma para o próximo ano** (copiar a turma e seus alunos para um novo ano
  letivo) ainda não existe. Esta mudança prepara o terreno; a cópia é um passo seguinte.
- O roteiro do vídeo (`scripts/demo_video.cjs`) não foi alterado nem reexecutado: ele associa
  a professora a uma turma ainda sem matérias, caso em que o comportamento é o mesmo de antes.
- Não executados: `ci.py` completo, Postman e ensaio de atualização. A mudança não toca
  imagem, infraestrutura, migrations nem autenticação.
