# Turmas — registrar a turma na matéria (24/11/2026)

Tela alterada: `/admin/turmas` (secretaria). Nenhuma captura anterior foi sobrescrita.

**O que mudou na tela**

- Nova seção logo abaixo de "Nova Turma": formulário **Registrar Turma na Matéria** (turma +
  matéria) e a lista **Matérias por Turma**, com a quantidade de alunos e o botão **Retirar**.
- A antiga lista "Disciplinas puxadas dos Professores", no rodapé, foi substituída por essa
  lista (agora com contagem de alunos e retirada).
- Textos de "Associar Aluno" e "Associar Professor" explicam a nova regra.

Componentes reaproveitados da própria tela: `turma-card`, `turma-field`, `turma-submit`,
`turma-link-item`, `turma-empty`. Único estilo novo: `.turma-remove` e `.turma-link-side` em
`admin_turmas.css`, nos mesmos tons dos cartões vizinhos.

| Captura | Tamanho | O que mostra |
| --- | --- | --- |
| [admin-turmas-materias-desktop.png](admin-turmas-materias-desktop.png) | 1440×1000 | Formulário e lista com três matérias da turma (20 alunos cada) |
| [admin-turmas-materias-celular.png](admin-turmas-materias-celular.png) | 390×844 | A mesma seção empilhada; item quebra em duas linhas, sem rolagem horizontal |
| [admin-turmas-materia-registrada-desktop.png](admin-turmas-materia-registrada-desktop.png) | 1440×1000 | Turma nova (2º ano A) registrada em Matemática, com 1 aluno associado depois |

**Limitação observada:** na captura do celular aparece no topo a faixa "Pular para o conteudo".
É o link de acessibilidade já existente da página, visível quando recebe o foco do teclado;
não foi introduzido por esta mudança.
