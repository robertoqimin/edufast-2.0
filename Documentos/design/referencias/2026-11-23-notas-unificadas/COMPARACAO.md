# Notas unificadas (B1) — comparação visual de 23/11/2026

Base: painéis de professor e aluno da galeria de 30/10/2026-r2. Mantidos DM Sans local,
menu, topbar, cartões, pílulas e tabelas dos próprios painéis. **Nenhum CSS novo**: as telas
reutilizam `professor-doc-block`, `professor-doc-item`, `professor-pill`,
`professor-request-status-*` e a tabela do painel do aluno. Nenhuma captura histórica foi
substituída. As imagens mostram somente dados fictícios.

## O que mudou

- **Professor, aba "Notas e avaliações"** (antes "Lançar notas"): o formulário de nota por
  aluno e disciplina saiu. No lugar dele aparece cada disciplina atribuída, com suas avaliações,
  período, peso, quantas notas foram lançadas, quantas aguardam aprovação e o estado
  (Rascunho, Publicação aguardando aprovação, Publicada). "Abrir diário" leva ao diário da
  avaliação.
- **Professor, aba "Minhas turmas"**: a tabela de alunos não tem mais campos de nota, só nome e
  matrícula, com um aviso de onde as notas são lançadas.
- **Aluno, "Minhas notas"**: o resumo vem do boletim publicado (disciplina, período, notas
  publicadas, média e situação), com link para o boletim completo. Registros antigos aparecem
  só como aviso, sem número, porque não entram na média.
- **Secretaria, detalhe do professor**: "Últimas notas lançadas" vem do diário e mostra
  disciplina, avaliação e período.

## Verificações

Edge headless em 1440×1000 e 390×844, nas 8 capturas: nenhuma rolagem horizontal da página
(largura do documento igual à da janela). O único erro de console foi o `favicon.ico`
ausente (404), que já existia. As tabelas viram cartões empilhados no celular pelo
comportamento existente.

**Limitação que já existia:** ao trocar de aba no painel do professor ou do aluno, o item
"Minhas turmas"/"Disciplinas" continua destacado no menu. O script das abas troca o painel,
mas não remove a classe `active` que o template põe na primeira aba. Isso não foi alterado
nesta etapa.

| Tela | Desktop | Celular |
| --- | --- | --- |
| Professor — Notas e avaliações | [Abrir](professor-notas-desktop.png) | [Abrir](professor-notas-celular.png) |
| Professor — Minhas turmas | [Abrir](professor-turmas-desktop.png) | [Abrir](professor-turmas-celular.png) |
| Aluno — Minhas notas | [Abrir](aluno-notas-desktop.png) | [Abrir](aluno-notas-celular.png) |
| Secretaria — detalhe do professor | [Abrir](admin-professor-desktop.png) | [Abrir](admin-professor-celular.png) |
