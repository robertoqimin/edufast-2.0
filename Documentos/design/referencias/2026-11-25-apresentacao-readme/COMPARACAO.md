# Apresentação do README — capturas de 25/11/2026

São 14 capturas da versão atual: 11 em desktop (1440×900) e 3 em celular (390×844). Elas
saíram da demo completa recriada do zero (`node infra/demo-completa.cjs reset`), com o
Colégio Horizonte e o painel Supremo, e usam somente dados fictícios. O README da raiz usa
estas imagens como apresentação do sistema.

Como gerar de novo: `node Codigos/tests/capturar_apresentacao_readme.cjs <pasta>`. O
manifesto registra o arquivo, a tela, o endereço, o viewport e o SHA-256 de cada imagem,
e as falhas da execução (nenhuma).

## Mudança visual encontrada na inspeção

| Tela | Antes ([`2026-11-25-u5-depois`](../2026-11-25-u5-depois/)) | Depois (esta pasta) |
| --- | --- | --- |
| Turmas, "Alunos matriculados" | Nomes separados por vírgula num parágrafo. Herdados do layout, os links viravam blocos e cada vírgula ficava sozinha numa linha | Lista de etiquetas (`ul.turma-alunos`) que quebram linha. Cada nome continua levando ao detalhe do aluno, e o foco do teclado fica visível na cor de destaque |

A mudança usa só os tokens do design system (`--line`, `--text`, `--accent`) e vale para os
temas claro e escuro. Nenhuma outra tela mudou.

## Limitações

- As capturas foram feitas no Edge sem janela (headless).
- Na tela da videoaula, o vídeo aparece parado aos 4 segundos, sem som.
- Para mostrar a aprovação em lote, o roteiro deixa pendente o lançamento do Simulado.
  Depois das capturas, a demo foi recriada.
