# B3 — comparação visual de 23/11/2026

Nenhum CSS novo e nenhuma captura histórica alterada. Somente dados fictícios.

## Seletor de turma no diário da secretaria

O `/academico` da secretaria mostra uma turma por vez. O seletor "Turma exibida" usa o
formulário (`course-form`), o rótulo e o botão secundário já existentes. Em 1440×1000 e
390×844 não há rolagem horizontal.

| Tela | Desktop | Celular |
| --- | --- | --- |
| Secretaria — Diário e avaliações | [Abrir](secretaria-academico-desktop.png) | [Abrir](secretaria-academico-celular.png) |

## Painéis sem React

O shell das páginas antigas passou a usar JavaScript simples. Foram feitas 32 capturas
antes/depois, em 16 telas e abas, desktop e celular:
- painel, cadastros, turmas, disciplinas, comunicados, banco de dados e detalhes da secretaria;
- abas do professor;
- abas e disciplina do aluno.

As capturas foram comparadas pixel a pixel. **24 ficaram idênticas.** As 8 diferenças são
horários de criação de registros, porque a escola de teste foi recriada entre as duas
rodadas (conferido lado a lado), ou 1 pixel do cursor de texto. Não houve erros de
JavaScript nem rolagem horizontal. Duas capturas de depois ficam aqui como referência.

| Tela | Captura |
| --- | --- |
| Professor — painel (desktop) | [Abrir](professor-painel-sem-react-desktop.png) |
| Aluno — painel (celular) | [Abrir](aluno-painel-sem-react-celular.png) |
